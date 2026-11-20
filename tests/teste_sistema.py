# -*- coding: utf-8 -*-
"""
Testes simples do Neighborhood Action Dashboard (sem bibliotecas externas).
Executar a partir da raiz do repositório:
    python tests/teste_sistema.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import sistema as s  # noqa: E402

resultados = []


def verificar(descricao, condicao):
    resultados.append(condicao)
    print(("[PASSOU] " if condicao else "[FALHOU] ") + descricao)


# --- Carga e validação dos dados -------------------------------------------
sis = s.iniciar_sistema()
verificar("12 ocorrências válidas carregadas", len(sis["ocorrencias"]) == 12)
verificar("2 registros rejeitados (sem categoria e duplicado)", len(sis["rejeitados"]) == 2)
verificar("Pelo menos 8 eventos no histórico", len(sis["historico"]) >= 8)
verificar("Histórico consistente com a situação atual", len(sis["avisos"]) == 0)
verificar("Fila inicial com as 5 abertas em ordem de registro",
          sis["fila"] == ["003", "007", "009", "011", "012"])

ind = s.calcular_indicadores(sis)
verificar("5 abertas, 4 em análise, 3 concluídas",
          ind["por_status"] == {"aberta": 5, "em_analise": 4, "concluida": 3})
verificar("Soma das categorias = total", sum(ind["por_categoria"].values()) == 12)
verificar("Tempo médio de conclusão = (5 + 6 + 8) / 3",
          abs(ind["tempo_medio_conclusao"] - 19 / 3) < 0.001)
soma_matriz = 0
for linha in ind["matriz"]:
    soma_matriz += sum(linha)
verificar("Matriz soma o total de ocorrências", soma_matriz == 12)

# --- Normalização de entradas ----------------------------------------------
verificar("'Iluminação' vira 'iluminacao'", s.interpretar_opcao("Iluminação", s.CATEGORIAS) == "iluminacao")
verificar("'Em Análise' vira 'em_analise'", s.interpretar_opcao("Em Análise", s.STATUS) == "em_analise")
verificar("Número 3 da lista de situações = concluida", s.interpretar_opcao("3", s.STATUS) == "concluida")
verificar("Texto desconhecido não é aceito", s.interpretar_opcao("resolvida", s.STATUS) is None)

# --- Cadastro ---------------------------------------------------------------
ok, msgs, cod = s.cadastrar_ocorrencia(sis, "", "Poste caído", "Vila Aurora")
verificar("Cadastro sem categoria é recusado", not ok and cod is None)
ok, msgs, cod = s.cadastrar_ocorrencia(sis, "buraco", "Buraco na rua", "Vila Aurora")
verificar("Categoria desconhecida é recusada", not ok)
ok, msgs, cod = s.cadastrar_ocorrencia(sis, "limpeza", "Ligar para 11987654321", "Vila Aurora")
verificar("Descrição com telefone é recusada (privacidade)", not ok)
ok, msgs, cod = s.cadastrar_ocorrencia(sis, "limpeza", "Lixo na praça", "")
verificar("Cadastro sem bairro é recusado", not ok)
ok, msgs, cod = s.cadastrar_ocorrencia(sis, "iluminação", "Refletor apagado", "Vila Aurora", "Praça Central")
verificar("Cadastro válido gera o código 014 (013 não é reaproveitado)", ok and cod == "014")
verificar("Nova ocorrência entra no fim da fila", sis["fila"][-1] == "014")
verificar("Busca por '14' encontra a ocorrência 014", s.buscar_por_id(sis, "14") is not None)
verificar("Busca por código inexistente retorna None", s.buscar_por_id(sis, "099") is None)

# --- Filtros ----------------------------------------------------------------
abertas_ilum = s.filtrar(sis["ocorrencias"], "iluminacao", "aberta")
verificar("Filtro abertas de iluminação = 011 e 014",
          [oc["id"] for oc in abertas_ilum] == ["011", "014"])
verificar("Filtro sem critérios devolve tudo", len(s.filtrar(sis["ocorrencias"])) == 13)

# --- Atualização de situação ------------------------------------------------
eventos_antes = len(sis["historico"])
ok, msg = s.atualizar_status(sis, "014", "em análise")
verificar("014 passa para em análise", ok and sis["indice"]["014"]["status"] == "em_analise")
verificar("Atualização gera evento no histórico", len(sis["historico"]) == eventos_antes + 1)
verificar("014 sai da fila", "014" not in sis["fila"])
verificar("Topo da pilha é a última atualização", s.consultar_topo(sis["pilha"], 1)[0]["id"] == "014")
ok, msg = s.atualizar_status(sis, "003", "concluida")
verificar("Aberta -> concluída é bloqueada", not ok)
ok, msg = s.atualizar_status(sis, "001", "aberta")
verificar("Concluída não pode mudar", not ok)
ok, msg = s.atualizar_status(sis, "007", "resolvida")
verificar("Situação desconhecida é recusada", not ok)
ok, msg = s.atualizar_status(sis, "999", "concluida")
verificar("Código inexistente informa 'não encontrada'", not ok and "não encontrada" in msg)
ok, msg = s.atualizar_status(sis, "014", "aberta")
verificar("Em análise -> aberta devolve ao fim da fila", ok and sis["fila"][-1] == "014")

# --- Fila (FIFO) ------------------------------------------------------------
ok, msg = s.examinar_proxima(sis)
verificar("Triagem retira a primeira da fila (003)", ok and sis["indice"]["003"]["status"] == "em_analise")

# --- Ordenação e hierarquia -------------------------------------------------
ordenadas = s.ordenar_por_antiguidade(sis["ocorrencias"])
crescente = True
for i in range(1, len(ordenadas)):
    if ordenadas[i - 1]["dia_abertura"] > ordenadas[i]["dia_abertura"]:
        crescente = False
verificar("Ordenação por inserção deixa os dias em ordem crescente", crescente)
arvore = s.montar_hierarquia(sis["ocorrencias"])
verificar("Hierarquia: Vila Aurora -> iluminação contém 001 e 014",
          arvore["Vila Aurora"]["iluminacao"] == ["001", "014"])

# --- Conclusão --------------------------------------------------------------
sis2 = s.iniciar_sistema()
s.avancar_dia(sis2, 5)
ok, msg = s.atualizar_status(sis2, "002", "concluida")
verificar("Conclusão no dia 25 registra dia_conclusao", sis2["indice"]["002"]["dia_conclusao"] == 25)

print()
print(str(resultados.count(True)) + " de " + str(len(resultados)) + " testes passaram.")
if False in resultados:
    sys.exit(1)
