# -*- coding: utf-8 -*-
"""
NEIGHBORHOOD ACTION DASHBOARD
Global Solution 2026.2 - FIAP - Desafio CitizenTech
Autor: Thiago Henrique Campos de Souza Giuliani - RM576080

Painel comunitário (em modo texto) para registrar, organizar e acompanhar
demandas de melhoria em bairros: iluminação, acessibilidade, limpeza e
conservação de espaços coletivos.

Como executar (a partir da raiz do repositório):
    python src/sistema.py          -> menu interativo
    python src/sistema.py --demo   -> roteiro automático de demonstração

Somente Python básico: funções, condicionais, laços, listas, dicionários,
fila, pilha, matriz e leitura de arquivo texto. Sem bibliotecas externas.

Estruturas de dados usadas (detalhes no README):
    LISTA       sistema["ocorrencias"]  -> conjunto de todas as ocorrências
    DICIONÁRIO  sistema["indice"]       -> acesso direto pelo código (id)
    FILA        sistema["fila"]         -> ocorrências abertas aguardando triagem
    PILHA       sistema["pilha"]        -> eventos mais recentes no topo
    HIERARQUIA  montar_hierarquia()     -> bairro -> categoria -> ocorrências
    MATRIZ      montar_matriz()         -> quantidades categoria x situação
"""

import os
import sys

# ---------------------------------------------------------------------------
# 1. CONFIGURAÇÕES E VALORES PADRONIZADOS
# ---------------------------------------------------------------------------

DIR_BASE = os.path.dirname(os.path.abspath(__file__))
ARQ_DADOS = os.path.join(DIR_BASE, "..", "data", "dados.csv")
ARQ_HISTORICO = os.path.join(DIR_BASE, "..", "data", "historico.csv")

SEPARADOR = ";"

# Campos que caracterizam uma ocorrência (na ordem das colunas do CSV)
CAMPOS = ["id", "categoria", "descricao", "bairro", "local", "dia_abertura", "status"]

# Campos obrigatórios. "local" é opcional: se vier vazio, vira "Local não informado".
OBRIGATORIOS = ["id", "categoria", "descricao", "bairro", "dia_abertura", "status"]

# Códigos padronizados (sem acento, minúsculos) -> rótulo para exibição
CATEGORIAS = {
    "iluminacao": "Iluminação",
    "acessibilidade": "Acessibilidade",
    "limpeza": "Limpeza",
    "conservacao": "Conservação",
}

STATUS = {
    "aberta": "Aberta",
    "em_analise": "Em análise",
    "concluida": "Concluída",
}

SIGNIFICADO_STATUS = {
    "aberta": "Registrada pela comunidade e aguardando triagem (está na fila).",
    "em_analise": "Já examinada; a demanda está sendo verificada ou encaminhada.",
    "concluida": "Problema resolvido; a ocorrência sai da lista de pendências.",
}

# Mudanças de situação permitidas (regra de negócio)
#   aberta     -> em_analise           (triagem)
#   em_analise -> concluida            (resolvida)
#   em_analise -> aberta               (devolvida: faltou informação)
#   concluida  -> (nenhuma)            (situação final)
TRANSICOES = {
    "aberta": ["em_analise"],
    "em_analise": ["concluida", "aberta"],
    "concluida": [],
}

# Palavras alternativas aceitas na digitação (deixa a interface mais tolerante)
SINONIMOS = {
    "luz": "iluminacao",
    "conservacao_de_espacos_coletivos": "conservacao",
    "aberto": "aberta",
    "analise": "em_analise",
    "em_analise": "em_analise",
    "concluido": "concluida",
}

CATEGORIAS_SEGURANCA = ["iluminacao", "acessibilidade"]  # afetam segurança/mobilidade
LIMITE_ATRASO = 7          # dias simulados para considerar uma pendência atrasada
MAX_DESCRICAO = 120        # tamanho máximo da descrição
DIA_INICIAL = 20           # "hoje" na simulação, ao abrir o sistema

# Tabela para remover acentos (usada para padronizar o que o usuário digita)
TABELA_ACENTOS = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüç",
                               "aaaaaeeeeiiiiooooouuuuc")


# ---------------------------------------------------------------------------
# 2. ESTADO DO SISTEMA
# ---------------------------------------------------------------------------

def criar_sistema(dia_atual=DIA_INICIAL):
    """Cria o dicionário que guarda todas as estruturas do programa."""
    return {
        "ocorrencias": [],   # LISTA de dicionários (uma ocorrência cada)
        "indice": {},        # DICIONÁRIO id -> ocorrência
        "fila": [],          # FILA (FIFO) de ids com situação "aberta"
        "pilha": [],         # PILHA (LIFO) de eventos; topo = mais recente
        "historico": [],     # todos os eventos em ordem cronológica
        "lidos": 0,          # quantidade de registros lidos do arquivo
        "rejeitados": [],    # registros do arquivo que não passaram na validação
        "avisos": [],        # inconsistências que não impedem o uso do registro
        "ids_usados": set(), # todos os códigos já lidos (nunca são reaproveitados)
        "dia_atual": dia_atual,
    }


# ---------------------------------------------------------------------------
# 3. FUNÇÕES DE APOIO (texto e interpretação de entradas)
# ---------------------------------------------------------------------------

def normalizar(texto):
    """'Em Análise ' -> 'em_analise'. Permite comparar entradas digitadas."""
    t = texto.strip().lower().translate(TABELA_ACENTOS)
    t = t.replace("-", " ")
    partes = t.split()
    return "_".join(partes)


def interpretar_opcao(texto, opcoes):
    """Converte o texto digitado (nome, sinônimo ou número da lista) em um código
    válido de 'opcoes'. Retorna None se não reconhecer."""
    if texto is None:
        return None
    n = normalizar(texto)
    codigos = list(opcoes)
    if n.isdigit():
        posicao = int(n)
        if 1 <= posicao <= len(codigos):
            return codigos[posicao - 1]
        return None
    if n in opcoes:
        return n
    if n in SINONIMOS and SINONIMOS[n] in opcoes:
        return SINONIMOS[n]
    return None


def padronizar_id(texto):
    """'14' -> '014'. Códigos têm sempre 3 dígitos."""
    t = texto.strip()
    if t.isdigit() and len(t) <= 3:
        return t.zfill(3)
    return t


def contar_digitos(texto):
    total = 0
    for caractere in texto:
        if caractere.isdigit():
            total += 1
    return total


def percentual(parte, total):
    if total == 0:
        return 0.0
    return parte / total * 100


def cortar(texto, largura):
    """Ajusta o texto a uma coluna de 'largura' caracteres (sempre com 1 espaço
    no final, para as colunas nunca grudarem)."""
    texto = str(texto)
    if len(texto) <= largura - 1:
        return texto.ljust(largura)
    return texto[: largura - 4] + "... "


def eh_pendente(oc):
    # Operador OR: pendente é o que ainda não foi concluído
    return oc["status"] == "aberta" or oc["status"] == "em_analise"


def dias_em_acompanhamento(oc, dia_atual):
    """Tempo simulado de acompanhamento: até a conclusão ou até hoje."""
    if oc["status"] == "concluida" and oc["dia_conclusao"] is not None:
        return oc["dia_conclusao"] - oc["dia_abertura"]
    return dia_atual - oc["dia_abertura"]


def eh_atrasada(oc, dia_atual):
    # AND + NOT: pendente E não concluída há mais de LIMITE_ATRASO dias
    return eh_pendente(oc) and not (dia_atual - oc["dia_abertura"] <= LIMITE_ATRASO)


def eh_prioritaria(oc, dia_atual):
    # Expressão booleana documentada no README:
    # atrasada AND (categoria == iluminacao OR categoria == acessibilidade)
    return eh_atrasada(oc, dia_atual) and (
        oc["categoria"] == "iluminacao" or oc["categoria"] == "acessibilidade")


# ---------------------------------------------------------------------------
# 4. VALIDAÇÃO
# ---------------------------------------------------------------------------

def validar_registro(reg, ids_existentes, dia_atual):
    """Recebe um registro com valores em texto e devolve a lista de erros.
    Lista vazia = registro válido."""
    erros = []

    # 4.1 Campos obrigatórios
    for campo in OBRIGATORIOS:
        valor = reg.get(campo, "")
        if valor is None or str(valor).strip() == "":
            erros.append("campo obrigatório '" + campo + "' está vazio")

    # 4.2 Código: 3 dígitos e sem repetição
    codigo = reg.get("id", "")
    if codigo != "" and not (codigo.isdigit() and len(codigo) == 3):
        erros.append("código '" + codigo + "' deve ter 3 dígitos (ex.: 014)")
    elif codigo in ids_existentes:
        erros.append("código '" + codigo + "' já existe (registro duplicado)")

    # 4.3 Categoria e situação precisam ser valores padronizados
    categoria = reg.get("categoria", "")
    if categoria != "" and categoria not in CATEGORIAS:
        erros.append("categoria desconhecida: '" + categoria + "'")

    status = reg.get("status", "")
    if status != "" and status not in STATUS:
        erros.append("situação desconhecida: '" + status + "'")

    # 4.4 Dia de abertura: número inteiro entre 1 e o dia atual da simulação
    dia = str(reg.get("dia_abertura", "")).strip()
    if dia != "":
        if not dia.isdigit():
            erros.append("dia de abertura '" + dia + "' não é um número inteiro")
        elif int(dia) < 1 or int(dia) > dia_atual:
            erros.append("dia de abertura fora do período simulado (1 a "
                         + str(dia_atual) + ")")

    # 4.5 Descrição: tamanho máximo e cuidado com privacidade
    descricao = reg.get("descricao", "")
    if len(descricao) > MAX_DESCRICAO:
        erros.append("descrição com mais de " + str(MAX_DESCRICAO) + " caracteres")
    if "@" in descricao or contar_digitos(descricao) >= 8:
        erros.append("descrição parece conter dado pessoal (e-mail, telefone ou "
                     "documento); descreva apenas o problema")

    return erros


# ---------------------------------------------------------------------------
# 5. OPERAÇÕES BÁSICAS DAS ESTRUTURAS
# ---------------------------------------------------------------------------

# FILA (primeiro a entrar, primeiro a sair)
def enfileirar(fila, codigo):
    fila.append(codigo)


def desenfileirar(fila):
    if len(fila) == 0:
        return None
    return fila.pop(0)


# PILHA (último a entrar, primeiro a sair)
def empilhar(pilha, evento):
    pilha.append(evento)


def consultar_topo(pilha, quantidade):
    """Devolve os 'quantidade' eventos mais recentes sem retirá-los da pilha."""
    recentes = []
    i = len(pilha) - 1
    while i >= 0 and len(recentes) < quantidade:
        recentes.append(pilha[i])
        i -= 1
    return recentes


def registrar_evento(sistema, codigo, dia, anterior, novo, observacao):
    evento = {"id": codigo, "dia": dia, "de": anterior, "para": novo,
              "obs": observacao}
    sistema["historico"].append(evento)
    empilhar(sistema["pilha"], evento)


def adicionar_ocorrencia(sistema, reg):
    """Insere um registro JÁ VALIDADO na lista, no índice e (se aberta) na fila."""
    local = reg.get("local", "").strip()
    oc = {
        "id": reg["id"],
        "categoria": reg["categoria"],
        "descricao": reg["descricao"].strip(),
        "bairro": reg["bairro"].strip(),
        "local": local if local != "" else "Local não informado",
        "dia_abertura": int(reg["dia_abertura"]),
        "status": reg["status"],
        "dia_conclusao": None,
    }
    sistema["ocorrencias"].append(oc)        # LISTA
    sistema["indice"][oc["id"]] = oc         # DICIONÁRIO
    sistema["ids_usados"].add(oc["id"])
    if oc["status"] == "aberta":
        enfileirar(sistema["fila"], oc["id"])  # FILA
    return oc


# ---------------------------------------------------------------------------
# 6. LEITURA DOS ARQUIVOS
# ---------------------------------------------------------------------------

def ler_linhas(caminho):
    with open(caminho, "r", encoding="utf-8") as arquivo:
        return arquivo.readlines()


def carregar_ocorrencias(sistema, caminho=ARQ_DADOS):
    linhas = ler_linhas(caminho)
    for numero in range(1, len(linhas)):      # linha 0 = cabeçalho
        linha = linhas[numero].strip()
        if linha == "" or linha.startswith("#"):
            continue
        sistema["lidos"] += 1
        partes = linha.split(SEPARADOR)
        if len(partes) != len(CAMPOS):
            sistema["rejeitados"].append({
                "linha": numero + 1, "id": "?",
                "erros": ["esperados " + str(len(CAMPOS)) + " campos, encontrados "
                          + str(len(partes))]})
            continue

        reg = {}
        for i in range(len(CAMPOS)):
            reg[CAMPOS[i]] = partes[i].strip()
        reg["categoria"] = normalizar(reg["categoria"])
        reg["status"] = normalizar(reg["status"])

        erros = validar_registro(reg, sistema["indice"], sistema["dia_atual"])
        if reg["id"] != "":
            sistema["ids_usados"].add(reg["id"])
        if len(erros) > 0:
            sistema["rejeitados"].append({"linha": numero + 1,
                                          "id": reg["id"] or "?", "erros": erros})
        else:
            adicionar_ocorrencia(sistema, reg)


def carregar_historico(sistema, caminho=ARQ_HISTORICO):
    linhas = ler_linhas(caminho)
    for numero in range(1, len(linhas)):
        linha = linhas[numero].strip()
        if linha == "":
            continue
        partes = linha.split(SEPARADOR)
        if len(partes) != 5:
            sistema["avisos"].append("histórico, linha " + str(numero + 1)
                                     + ": formato inválido, evento ignorado")
            continue
        codigo, dia, anterior, novo, obs = [p.strip() for p in partes]
        oc = sistema["indice"].get(codigo)
        if oc is None or not dia.isdigit() or novo not in STATUS:
            sistema["avisos"].append("histórico, linha " + str(numero + 1)
                                     + ": evento da ocorrência '" + codigo
                                     + "' ignorado (código ou dados inválidos)")
            continue
        registrar_evento(sistema, codigo, int(dia), anterior, novo, obs)
        if novo == "concluida":
            oc["dia_conclusao"] = int(dia)

    # Conferência: a última situação do histórico deve ser a situação atual
    for oc in sistema["ocorrencias"]:
        ultima = None
        for ev in sistema["historico"]:
            if ev["id"] == oc["id"]:
                ultima = ev["para"]
        if ultima is not None and ultima != oc["status"]:
            sistema["avisos"].append("ocorrência " + oc["id"] + ": histórico termina em '"
                                     + ultima + "', mas a situação atual é '"
                                     + oc["status"] + "'")
        if oc["status"] == "concluida" and oc["dia_conclusao"] is None:
            sistema["avisos"].append("ocorrência " + oc["id"] + ": concluída sem dia de "
                                     "conclusão no histórico (fora do tempo médio)")


def iniciar_sistema(dia_atual=DIA_INICIAL):
    sistema = criar_sistema(dia_atual)
    carregar_ocorrencias(sistema)
    carregar_historico(sistema)
    return sistema


# ---------------------------------------------------------------------------
# 7. CADASTRO, CONSULTA E ATUALIZAÇÃO
# ---------------------------------------------------------------------------

def proximo_id(sistema):
    """Maior código já lido + 1. Inclui códigos rejeitados, para nunca reaproveitar
    um número que já apareceu nos dados."""
    maior = 0
    for codigo in sistema["ids_usados"]:
        if codigo.isdigit() and int(codigo) > maior:
            maior = int(codigo)
    return str(maior + 1).zfill(3)


def cadastrar_ocorrencia(sistema, categoria, descricao, bairro, local="", dia=None):
    """Cadastra uma nova ocorrência (sempre começa como 'aberta').
    Retorna (sucesso, mensagens, codigo)."""
    categoria_cod = interpretar_opcao(categoria, CATEGORIAS)
    if dia is None or str(dia).strip() == "":
        dia = sistema["dia_atual"]
    reg = {
        "id": proximo_id(sistema),
        # Se a categoria não foi reconhecida, guardamos o texto normalizado para
        # que a validação explique o problema ("vazia" ou "desconhecida").
        "categoria": categoria_cod if categoria_cod else normalizar(categoria or ""),
        "descricao": (descricao or "").strip(),
        "bairro": (bairro or "").strip(),
        "local": (local or "").strip(),
        "dia_abertura": str(dia).strip(),
        "status": "aberta",
    }
    erros = validar_registro(reg, sistema["indice"], sistema["dia_atual"])
    if len(erros) > 0:
        return False, erros, None
    oc = adicionar_ocorrencia(sistema, reg)
    registrar_evento(sistema, oc["id"], oc["dia_abertura"], "-", "aberta",
                     "Cadastro de nova ocorrência")
    return True, ["Ocorrência " + oc["id"] + " cadastrada e colocada na fila de triagem."], oc["id"]


def buscar_por_id(sistema, codigo):
    """Busca direta no dicionário: não precisa percorrer a lista."""
    return sistema["indice"].get(padronizar_id(codigo))


def filtrar(ocorrencias, categoria=None, status=None):
    """Busca sequencial com filtros combináveis. None = sem filtro."""
    resultado = []
    for oc in ocorrencias:
        # AND entre os filtros; OR dentro de cada um para aceitar "sem filtro"
        if (categoria is None or oc["categoria"] == categoria) and \
           (status is None or oc["status"] == status):
            resultado.append(oc)
    return resultado


def historico_da_ocorrencia(sistema, codigo):
    eventos = []
    for ev in sistema["historico"]:
        if ev["id"] == codigo:
            eventos.append(ev)
    return eventos


def atualizar_status(sistema, codigo, novo_texto, observacao=""):
    """Muda a situação respeitando TRANSICOES. Retorna (sucesso, mensagem)."""
    codigo = padronizar_id(codigo)
    oc = sistema["indice"].get(codigo)
    if oc is None:
        return False, "Ocorrência '" + codigo + "' não encontrada. Confira o código."

    novo = interpretar_opcao(novo_texto, STATUS)
    atual = oc["status"]

    if novo is None:
        return False, ("Situação desconhecida: '" + str(novo_texto) + "'. Use: "
                       + ", ".join(STATUS.values()) + ".")
    elif novo == atual:
        return False, "A ocorrência " + codigo + " já está '" + STATUS[atual] + "'."
    elif novo not in TRANSICOES[atual]:
        if len(TRANSICOES[atual]) == 0:
            permitidas = "nenhuma (situação final)"
        else:
            permitidas = ", ".join([STATUS[s] for s in TRANSICOES[atual]])
        return False, ("Mudança não permitida: " + STATUS[atual] + " -> " + STATUS[novo]
                       + ". A partir de '" + STATUS[atual] + "' é permitido: "
                       + permitidas + ".")
    else:
        oc["status"] = novo
        if novo == "concluida":
            oc["dia_conclusao"] = sistema["dia_atual"]
        # Manutenção da fila: quem sai de "aberta" deixa a fila;
        # quem volta para "aberta" entra no fim da fila.
        if atual == "aberta" and codigo in sistema["fila"]:
            sistema["fila"].remove(codigo)
        if novo == "aberta":
            enfileirar(sistema["fila"], codigo)
        if observacao.strip() == "":
            observacao = "Atualização registrada pelo painel"
        registrar_evento(sistema, codigo, sistema["dia_atual"], atual, novo, observacao)
        return True, ("Ocorrência " + codigo + ": " + STATUS[atual] + " -> "
                      + STATUS[novo] + " (dia " + str(sistema["dia_atual"])
                      + "). Alteração registrada no histórico.")


def examinar_proxima(sistema):
    """Retira a primeira ocorrência da fila e a coloca 'em análise'."""
    codigo = desenfileirar(sistema["fila"])
    if codigo is None:
        return False, "A fila de triagem está vazia: não há ocorrências abertas."
    return atualizar_status(sistema, codigo, "em_analise",
                            "Retirada da fila de triagem para análise")


def ordenar_por_antiguidade(ocorrencias):
    """Ordenação por inserção (insertion sort): da abertura mais antiga para a mais
    recente. Usada para listar as pendências que esperam há mais tempo."""
    lista = ocorrencias[:]  # cópia, para não alterar a lista original
    for i in range(1, len(lista)):
        atual = lista[i]
        j = i - 1
        while j >= 0 and lista[j]["dia_abertura"] > atual["dia_abertura"]:
            lista[j + 1] = lista[j]
            j -= 1
        lista[j + 1] = atual
    return lista


def avancar_dia(sistema, dias):
    if dias < 1 or dias > 30:
        return False, "Informe um número de dias entre 1 e 30."
    sistema["dia_atual"] += dias
    return True, "Simulação avançada para o dia " + str(sistema["dia_atual"]) + "."


# ---------------------------------------------------------------------------
# 8. HIERARQUIA E MATRIZ
# ---------------------------------------------------------------------------

def montar_hierarquia(ocorrencias):
    """Árvore em dicionários aninhados: bairro -> categoria -> [códigos]."""
    arvore = {}
    for oc in ocorrencias:
        bairro = oc["bairro"]
        categoria = oc["categoria"]
        if bairro not in arvore:
            arvore[bairro] = {}
        if categoria not in arvore[bairro]:
            arvore[bairro][categoria] = []
        arvore[bairro][categoria].append(oc["id"])
    return arvore


def montar_matriz(ocorrencias):
    """Matriz (lista de listas): linha = categoria, coluna = situação."""
    categorias = list(CATEGORIAS)
    situacoes = list(STATUS)
    matriz = []
    for _ in categorias:
        matriz.append([0] * len(situacoes))
    for oc in ocorrencias:
        i = categorias.index(oc["categoria"])
        j = situacoes.index(oc["status"])
        matriz[i][j] += 1
    return matriz


# ---------------------------------------------------------------------------
# 9. INDICADORES
# ---------------------------------------------------------------------------

def calcular_indicadores(sistema):
    ocs = sistema["ocorrencias"]
    dia = sistema["dia_atual"]
    total = len(ocs)

    por_categoria = {}
    pendentes_por_categoria = {}
    for c in CATEGORIAS:
        por_categoria[c] = 0
        pendentes_por_categoria[c] = 0
    por_status = {}
    for s in STATUS:
        por_status[s] = 0

    soma_conclusao = 0
    qtd_conclusao = 0
    soma_espera = 0
    pendentes = []
    for oc in ocs:
        por_categoria[oc["categoria"]] += 1
        por_status[oc["status"]] += 1
        if eh_pendente(oc):
            pendentes.append(oc)
            pendentes_por_categoria[oc["categoria"]] += 1
            soma_espera += dia - oc["dia_abertura"]
        elif oc["dia_conclusao"] is not None:
            soma_conclusao += oc["dia_conclusao"] - oc["dia_abertura"]
            qtd_conclusao += 1

    atrasadas = []
    prioritarias = []
    for oc in pendentes:
        if eh_atrasada(oc, dia):
            atrasadas.append(oc["id"])
        if eh_prioritaria(oc, dia):
            prioritarias.append(oc["id"])

    return {
        "total": total,
        "por_categoria": por_categoria,
        "por_status": por_status,
        "pendentes_por_categoria": pendentes_por_categoria,
        "matriz": montar_matriz(ocs),
        "qtd_pendentes": len(pendentes),
        "taxa_conclusao": percentual(por_status["concluida"], total),
        "soma_conclusao": soma_conclusao,
        "qtd_conclusao": qtd_conclusao,
        "tempo_medio_conclusao": soma_conclusao / qtd_conclusao if qtd_conclusao > 0 else 0.0,
        "espera_media_pendentes": soma_espera / len(pendentes) if len(pendentes) > 0 else 0.0,
        "atrasadas": atrasadas,
        "prioritarias": prioritarias,
    }


def maiores(contagem):
    """Devolve as chaves com o maior valor (considera empates)."""
    maior = -1
    for chave in contagem:
        if contagem[chave] > maior:
            maior = contagem[chave]
    nomes = []
    for chave in contagem:
        if contagem[chave] == maior:
            nomes.append(chave)
    return nomes, maior


def interpretar_indicadores(ind):
    """Conclusão breve em linguagem simples, gerada a partir dos números."""
    if ind["total"] == 0:
        return ["Não há ocorrências válidas para analisar."]
    textos = []
    cats, qtd = maiores(ind["por_categoria"])
    nomes = " e ".join([CATEGORIAS[c] for c in cats])
    if len(cats) == 1:
        textos.append("- " + nomes + " é a categoria com mais registros (" + str(qtd)
                      + ", " + format(percentual(qtd, ind["total"]), ".1f")
                      + "% do total).")
    else:
        textos.append("- " + nomes + " empatam com mais registros (" + str(qtd)
                      + " cada, " + format(percentual(qtd, ind["total"]), ".1f")
                      + "% do total cada).")
    cats_p, qtd_p = maiores(ind["pendentes_por_categoria"])
    if qtd_p > 0:
        textos.append("- A maior quantidade de pendências está em "
                      + " e ".join([CATEGORIAS[c] for c in cats_p]) + " ("
                      + str(qtd_p) + (" cada)." if len(cats_p) > 1 else ")."))
    textos.append("- " + format(percentual(ind["qtd_pendentes"], ind["total"]), ".1f")
                  + "% das demandas ainda não foram concluídas; o painel indica onde "
                  "a comunidade deve concentrar a cobrança e o acompanhamento.")
    if ind["qtd_conclusao"] > 0:
        textos.append("- Quando resolvidas, as demandas levaram em média "
                      + format(ind["tempo_medio_conclusao"], ".2f") + " dias simulados; "
                      "as pendentes já esperam em média "
                      + format(ind["espera_media_pendentes"], ".2f") + " dias.")
    if len(ind["prioritarias"]) > 0:
        textos.append("- Há " + str(len(ind["prioritarias"])) + " pendência(s) atrasada(s) "
                      "de iluminação ou acessibilidade (" + ", ".join(ind["prioritarias"])
                      + "), que afetam segurança e mobilidade e merecem atenção primeiro.")
    textos.append("- Atenção: os dados são simulados e não representam um bairro real.")
    return textos


# ---------------------------------------------------------------------------
# 10. EXIBIÇÃO (interface textual)
# ---------------------------------------------------------------------------

def titulo(texto):
    print()
    print("=" * 78)
    print(" " + texto.upper())
    print("=" * 78)


def barra(valor, total, largura=20):
    if total == 0:
        return ""
    return "#" * round(valor / total * largura)


def exibir_tabela(ocorrencias, dia_atual):
    if len(ocorrencias) == 0:
        print("Nenhuma ocorrência encontrada com esses critérios.")
        return
    print(cortar("Código", 7) + cortar("Categoria", 15) + cortar("Bairro", 18)
          + cortar("Local", 22) + cortar("Situação", 12) + "Dias")
    print("-" * 78)
    for oc in ocorrencias:
        print(cortar(oc["id"], 7) + cortar(CATEGORIAS[oc["categoria"]], 15)
              + cortar(oc["bairro"], 18) + cortar(oc["local"], 22)
              + cortar(STATUS[oc["status"]], 12)
              + str(dias_em_acompanhamento(oc, dia_atual)))
    print("-" * 78)
    print(str(len(ocorrencias)) + " ocorrência(s). 'Dias' = tempo simulado de "
          "acompanhamento (até a conclusão ou até hoje).")


def exibir_detalhes(sistema, oc):
    print("Código ........: " + oc["id"])
    print("Categoria .....: " + CATEGORIAS[oc["categoria"]])
    print("Descrição .....: " + oc["descricao"])
    print("Bairro ........: " + oc["bairro"])
    print("Local .........: " + oc["local"])
    print("Aberta no dia .: " + str(oc["dia_abertura"]))
    print("Situação ......: " + STATUS[oc["status"]] + " - "
          + SIGNIFICADO_STATUS[oc["status"]])
    if oc["dia_conclusao"] is not None:
        print("Concluída no dia: " + str(oc["dia_conclusao"]))
    print("Acompanhamento : " + str(dias_em_acompanhamento(oc, sistema["dia_atual"]))
          + " dia(s)")
    eventos = historico_da_ocorrencia(sistema, oc["id"])
    print("Histórico .....: " + (str(len(eventos)) + " evento(s)" if eventos else
                                 "sem eventos registrados"))
    for ev in eventos:
        print("   dia " + str(ev["dia"]).rjust(2) + ": " + ev["de"] + " -> "
              + ev["para"] + " | " + ev["obs"])


def exibir_eventos(eventos):
    if len(eventos) == 0:
        print("Nenhum evento registrado.")
        return
    for ev in eventos:
        print("dia " + str(ev["dia"]).rjust(2) + " | ocorrência " + ev["id"] + " | "
              + ev["de"] + " -> " + ev["para"] + " | " + ev["obs"])


def exibir_fila(sistema):
    fila = sistema["fila"]
    if len(fila) == 0:
        print("Fila vazia: todas as ocorrências já foram examinadas.")
        return
    print("Ordem de atendimento (a primeira será a próxima examinada):")
    posicao = 1
    for codigo in fila:
        oc = sistema["indice"][codigo]
        print(" " + str(posicao) + "º  " + codigo + "  " + cortar(CATEGORIAS[oc["categoria"]], 15)
              + cortar(oc["bairro"], 18) + "aberta no dia " + str(oc["dia_abertura"]))
        posicao += 1


def exibir_hierarquia(sistema):
    arvore = montar_hierarquia(sistema["ocorrencias"])
    for bairro in sorted(arvore):
        total_bairro = 0
        for cat in arvore[bairro]:
            total_bairro += len(arvore[bairro][cat])
        print(bairro + " (" + str(total_bairro) + " ocorrências)")
        for cat in CATEGORIAS:
            if cat in arvore[bairro]:
                codigos = arvore[bairro][cat]
                print("   +-- " + CATEGORIAS[cat] + " (" + str(len(codigos)) + "): "
                      + ", ".join(codigos))


def exibir_rejeitados(sistema):
    if len(sistema["rejeitados"]) == 0:
        print("Nenhum registro rejeitado.")
    for r in sistema["rejeitados"]:
        print("Linha " + str(r["linha"]) + " do arquivo (código " + r["id"] + "):")
        for e in r["erros"]:
            print("   - " + e)
    if len(sistema["avisos"]) > 0:
        print("Avisos de consistência:")
        for a in sistema["avisos"]:
            print("   - " + a)
    print("Regra: registros inválidos não entram na lista nem nos indicadores, "
          "e o código deles não é reaproveitado.")


def exibir_indicadores(sistema):
    ind = calcular_indicadores(sistema)
    total = ind["total"]

    titulo("Painel de indicadores - dia simulado " + str(sistema["dia_atual"]))
    print("DADOS DE ORIGEM")
    print("  Arquivo data/dados.csv: " + str(sistema["lidos"])
          + " registros lidos; " + str(len(sistema["rejeitados"]))
          + " rejeitados na validação.")
    print("  Ocorrências válidas no painel (inclui cadastros desta sessão): " + str(total))
    print("  Eventos no histórico: " + str(len(sistema["historico"])))

    print()
    print("1) OCORRÊNCIAS POR CATEGORIA   [proporção = quantidade / total x 100]")
    for c in CATEGORIAS:
        q = ind["por_categoria"][c]
        print("  " + cortar(CATEGORIAS[c], 16) + str(q).rjust(3) + "   "
              + format(percentual(q, total), "5.1f") + "%  " + barra(q, total))

    print()
    print("2) OCORRÊNCIAS POR SITUAÇÃO")
    for s in STATUS:
        q = ind["por_status"][s]
        print("  " + cortar(STATUS[s], 16) + str(q).rjust(3) + "   "
              + format(percentual(q, total), "5.1f") + "%  " + barra(q, total))

    print()
    print("3) MATRIZ CATEGORIA x SITUAÇÃO")
    situacoes = list(STATUS)
    print("  " + cortar("", 16) + "".join([cortar(STATUS[s], 12) for s in situacoes])
          + "Total")
    totais_colunas = [0] * len(situacoes)
    i = 0
    for c in CATEGORIAS:
        linha = ind["matriz"][i]
        soma_linha = 0
        for j in range(len(linha)):
            soma_linha += linha[j]
            totais_colunas[j] += linha[j]
        print("  " + cortar(CATEGORIAS[c], 16)
              + "".join([cortar(str(v), 12) for v in linha]) + str(soma_linha))
        i += 1
    print("  " + cortar("Total", 16) + "".join([cortar(str(v), 12) for v in totais_colunas])
          + str(total))

    print()
    print("4) INDICADORES ADICIONAIS")
    print("  Pendências (aberta + em análise) .........: " + str(ind["qtd_pendentes"])
          + "  (" + format(percentual(ind["qtd_pendentes"], total), ".1f") + "%)")
    print("  Taxa de conclusão (concluídas / total) ...: "
          + format(ind["taxa_conclusao"], ".1f") + "%")
    print("  Tempo médio até a conclusão ..............: "
          + format(ind["tempo_medio_conclusao"], ".2f") + " dias")
    print("     fórmula: soma(dia_conclusão - dia_abertura) / nº de concluídas = "
          + str(ind["soma_conclusao"]) + " / " + str(ind["qtd_conclusao"]))
    print("  Espera média das pendências ..............: "
          + format(ind["espera_media_pendentes"], ".2f") + " dias")
    print("     fórmula: soma(dia_atual - dia_abertura) / nº de pendências")
    print("  Pendências atrasadas (> " + str(LIMITE_ATRASO) + " dias) ..........: "
          + str(len(ind["atrasadas"])) + "  " + ", ".join(ind["atrasadas"]))
    print("  Atrasadas de iluminação/acessibilidade ...: "
          + str(len(ind["prioritarias"])) + "  " + ", ".join(ind["prioritarias"]))

    print()
    print("5) O QUE OS NÚMEROS SUGEREM")
    for t in interpretar_indicadores(ind):
        print("  " + t)


def exibir_ajuda():
    titulo("Ajuda - categorias e situações")
    print("Categorias (digite o nome, com ou sem acento, ou o número):")
    n = 1
    for c in CATEGORIAS:
        print("  " + str(n) + " - " + CATEGORIAS[c])
        n += 1
    print("Situações:")
    n = 1
    for s in STATUS:
        print("  " + str(n) + " - " + STATUS[s] + ": " + SIGNIFICADO_STATUS[s])
        n += 1
    print("Mudanças permitidas: Aberta -> Em análise -> Concluída;")
    print("                     Em análise -> Aberta (devolvida por falta de informação).")
    print("Privacidade: não informe nomes, telefones, e-mails ou documentos.")
    print("Use locais genéricos (ex.: 'Praça Central', 'ponto de ônibus').")


# ---------------------------------------------------------------------------
# 11. MENU INTERATIVO
# ---------------------------------------------------------------------------

def ler(mensagem):
    """input() protegido: Ctrl+D / Ctrl+C encerram o programa sem erro."""
    try:
        return input(mensagem)
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def listar_opcoes(opcoes):
    n = 1
    for codigo in opcoes:
        print("  " + str(n) + " - " + opcoes[codigo])
        n += 1


def menu_buscar(sistema):
    codigo = ler("Código da ocorrência (ex.: 014): ")
    if codigo is None or codigo.strip() == "":
        print("Nenhum código informado.")
        return
    oc = buscar_por_id(sistema, codigo)
    if oc is None:
        print("Ocorrência '" + padronizar_id(codigo) + "' não encontrada.")
    else:
        exibir_detalhes(sistema, oc)


def menu_filtrar(sistema):
    print("Categoria (Enter = todas):")
    listar_opcoes(CATEGORIAS)
    txt_cat = ler("> ")
    print("Situação (Enter = todas):")
    listar_opcoes(STATUS)
    txt_st = ler("> ")

    categoria = None
    status = None
    if txt_cat is not None and txt_cat.strip() != "":
        categoria = interpretar_opcao(txt_cat, CATEGORIAS)
        if categoria is None:
            print("Categoria '" + txt_cat + "' não reconhecida.")
            return
    if txt_st is not None and txt_st.strip() != "":
        status = interpretar_opcao(txt_st, STATUS)
        if status is None:
            print("Situação '" + txt_st + "' não reconhecida.")
            return
    resultado = filtrar(sistema["ocorrencias"], categoria, status)
    print("Filtro: categoria = " + (CATEGORIAS[categoria] if categoria else "todas")
          + "; situação = " + (STATUS[status] if status else "todas"))
    exibir_tabela(resultado, sistema["dia_atual"])


def menu_cadastrar(sistema):
    print("Novo código será: " + proximo_id(sistema) + ". Campos com * são obrigatórios.")
    print("Categoria*:")
    listar_opcoes(CATEGORIAS)
    categoria = ler("> ")
    descricao = ler("Descrição breve* (sem dados pessoais): ")
    bairros = sorted(montar_hierarquia(sistema["ocorrencias"]))
    print("Bairro* (digite o número ou um nome novo): ")
    for i in range(len(bairros)):
        print("  " + str(i + 1) + " - " + bairros[i])
    bairro = ler("> ")
    if bairro is not None and bairro.strip().isdigit():
        pos = int(bairro.strip())
        if 1 <= pos <= len(bairros):
            bairro = bairros[pos - 1]
    local = ler("Local genérico (opcional, ex.: Praça Central): ")
    dia = ler("Dia de abertura (Enter = hoje, dia " + str(sistema["dia_atual"]) + "): ")
    if None in (categoria, descricao, bairro):
        print("Cadastro cancelado.")
        return
    ok, mensagens, _ = cadastrar_ocorrencia(sistema, categoria, descricao, bairro,
                                             local or "", dia)
    if ok:
        print(mensagens[0])
    else:
        print("Cadastro NÃO realizado. Corrija os itens abaixo:")
        for m in mensagens:
            print("   - " + m)


def menu_atualizar(sistema):
    codigo = ler("Código da ocorrência: ")
    if codigo is None:
        return
    oc = buscar_por_id(sistema, codigo)
    if oc is None:
        print("Ocorrência '" + padronizar_id(codigo) + "' não encontrada.")
        return
    print("Situação atual: " + STATUS[oc["status"]])
    if len(TRANSICOES[oc["status"]]) == 0:
        print("Esta ocorrência está concluída; não há mudanças possíveis.")
        return
    print("Nova situação:")
    listar_opcoes(STATUS)
    novo = ler("> ")
    obs = ler("Observação (opcional): ") or ""
    ok, msg = atualizar_status(sistema, codigo, novo or "", obs)
    print(msg)


def menu_eventos(sistema):
    qtd = ler("Quantos eventos recentes deseja ver? (Enter = 5): ")
    if qtd is None or not qtd.strip().isdigit():
        qtd = "5"
    print("Eventos mais recentes primeiro (topo da pilha):")
    exibir_eventos(consultar_topo(sistema["pilha"], int(qtd)))


def menu_avancar(sistema):
    txt = ler("Avançar quantos dias? ")
    if txt is None or not txt.strip().isdigit():
        print("Valor inválido: digite um número inteiro.")
        return
    ok, msg = avancar_dia(sistema, int(txt))
    print(msg)


def menu_pendencias(sistema):
    pend = []
    for oc in sistema["ocorrencias"]:
        if eh_pendente(oc):
            pend.append(oc)
    print("Pendências da mais antiga para a mais recente (ordenação por inserção):")
    exibir_tabela(ordenar_por_antiguidade(pend), sistema["dia_atual"])


OPCOES_MENU = [
    ("1", "Listar todas as ocorrências"),
    ("2", "Buscar ocorrência por código (com histórico)"),
    ("3", "Filtrar por categoria e/ou situação"),
    ("4", "Cadastrar nova ocorrência"),
    ("5", "Atualizar situação de uma ocorrência"),
    ("6", "Examinar a próxima ocorrência da fila de triagem"),
    ("7", "Ver fila de triagem"),
    ("8", "Ver eventos recentes (pilha)"),
    ("9", "Ver pendências da mais antiga para a mais recente"),
    ("10", "Ver organização bairro -> categoria -> ocorrências"),
    ("11", "Painel de indicadores"),
    ("12", "Registros rejeitados e inconsistências"),
    ("13", "Avançar o dia simulado"),
    ("14", "Ajuda: categorias, situações e privacidade"),
    ("0", "Sair"),
]


def menu(sistema):
    titulo("Neighborhood Action Dashboard - painel comunitário de ocorrências")
    print(str(len(sistema["ocorrencias"])) + " ocorrências válidas carregadas; "
          + str(len(sistema["rejeitados"])) + " registro(s) rejeitado(s) na validação "
          "(opção 12).")
    while True:
        print()
        print("MENU - dia simulado " + str(sistema["dia_atual"]))
        for numero, texto in OPCOES_MENU:
            print("  " + numero.rjust(2) + " - " + texto)
        opcao = ler("Escolha uma opção: ")
        if opcao is None:
            break
        opcao = opcao.strip()

        if opcao == "0":
            break
        elif opcao == "1":
            titulo("Todas as ocorrências")
            exibir_tabela(sistema["ocorrencias"], sistema["dia_atual"])
        elif opcao == "2":
            titulo("Buscar por código")
            menu_buscar(sistema)
        elif opcao == "3":
            titulo("Filtrar ocorrências")
            menu_filtrar(sistema)
        elif opcao == "4":
            titulo("Cadastrar ocorrência")
            menu_cadastrar(sistema)
        elif opcao == "5":
            titulo("Atualizar situação")
            menu_atualizar(sistema)
        elif opcao == "6":
            titulo("Triagem")
            ok, msg = examinar_proxima(sistema)
            print(msg)
        elif opcao == "7":
            titulo("Fila de triagem")
            exibir_fila(sistema)
        elif opcao == "8":
            titulo("Eventos recentes")
            menu_eventos(sistema)
        elif opcao == "9":
            titulo("Pendências por antiguidade")
            menu_pendencias(sistema)
        elif opcao == "10":
            titulo("Bairro -> categoria -> ocorrências")
            exibir_hierarquia(sistema)
        elif opcao == "11":
            exibir_indicadores(sistema)
        elif opcao == "12":
            titulo("Validação dos dados")
            exibir_rejeitados(sistema)
        elif opcao == "13":
            menu_avancar(sistema)
        elif opcao == "14":
            exibir_ajuda()
        else:
            print("Opção '" + opcao + "' inválida. Digite um número de 0 a 14.")
    print("Até logo! As alterações desta sessão não são gravadas no arquivo.")


# ---------------------------------------------------------------------------
# 12. DEMONSTRAÇÃO AUTOMÁTICA (python src/sistema.py --demo)
# ---------------------------------------------------------------------------

def demonstracao():
    sistema = iniciar_sistema()

    titulo("Demo 1 - dados carregados")
    exibir_tabela(sistema["ocorrencias"], sistema["dia_atual"])

    titulo("Demo 2 - registros inconsistentes tratados pela validação")
    exibir_rejeitados(sistema)

    titulo("Demo 3 - cadastro inválido (sem categoria)")
    ok, msgs, _ = cadastrar_ocorrencia(sistema, "", "Poste caído na calçada",
                                       "Vila Aurora", "Rua lateral")
    for m in msgs:
        print("   - " + m)

    titulo("Demo 4 - cadastro válido (ação 1)")
    ok, msgs, codigo = cadastrar_ocorrencia(sistema, "iluminação",
                                            "Refletor da praça apagado",
                                            "Vila Aurora", "Praça Central")
    print(msgs[0])
    exibir_detalhes(sistema, buscar_por_id(sistema, codigo))

    titulo("Demo 5 - consulta: ocorrências ABERTAS de ILUMINAÇÃO")
    exibir_tabela(filtrar(sistema["ocorrencias"], "iluminacao", "aberta"),
                  sistema["dia_atual"])

    titulo("Demo 6 - busca por código inexistente")
    oc = buscar_por_id(sistema, "99")
    print("Ocorrência 099 não encontrada." if oc is None else oc["id"])

    titulo("Demo 7 - atualizações de situação (ação 2)")
    for cod, novo in [(codigo, "em análise"), ("003", "concluída"),
                      ("001", "aberta"), ("007", "resolvida"), ("002", "concluida")]:
        ok, msg = atualizar_status(sistema, cod, novo)
        print(("[OK]   " if ok else "[ERRO] ") + msg)

    titulo("Demo 8 - fila de triagem e próxima análise")
    exibir_fila(sistema)
    ok, msg = examinar_proxima(sistema)
    print(msg)

    titulo("Demo 9 - eventos recentes (topo da pilha)")
    exibir_eventos(consultar_topo(sistema["pilha"], 5))

    titulo("Demo 10 - hierarquia bairro -> categoria -> ocorrências")
    exibir_hierarquia(sistema)

    exibir_indicadores(sistema)  # ação 3


# ---------------------------------------------------------------------------
# 13. PONTO DE ENTRADA
# ---------------------------------------------------------------------------

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # acentos no terminal do Windows
    except (AttributeError, ValueError):
        pass
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demonstracao()
    else:
        try:
            sistema = iniciar_sistema()
        except FileNotFoundError as erro:
            print("Arquivo de dados não encontrado: " + str(erro.filename))
            print("Execute a partir da raiz do repositório: python src/sistema.py")
            return
        menu(sistema)


if __name__ == "__main__":
    main()
