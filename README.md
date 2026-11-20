# Neighborhood Action Dashboard

**Global Solution 2026.2 · FIAP · Desafio CitizenTech**

Painel comunitário em modo texto para **registrar, organizar e acompanhar demandas de melhoria em bairros**: iluminação, acessibilidade, limpeza e conservação de espaços coletivos. Feito apenas com Python básico (conteúdos das fases 1, 2 e 3), sem bibliotecas externas, banco de dados ou APIs.

---

## 1. Autor

| Nome | RM |
|---|---|
| Thiago Henrique Campos de Souza Giuliani | RM576080 |

Projeto desenvolvido individualmente.

**Vídeo de apresentação (YouTube, não listado):** https://youtu.be/825VtWG2Vag (o mesmo de `docs/link_video.txt`)

---

## 2. Comunidade simulada, problema e público

**Comunidade simulada.** Uma região fictícia formada por três bairros: **Vila Aurora**, **Jardim Primavera** e **Parque das Flores**. Os locais são genéricos (Praça Central, ponto de ônibus, quadra esportiva, calçada do posto de saúde…). Nenhum endereço, pessoa ou órgão real é mencionado.

**Problema.** Problemas de infraestrutura (poste apagado, calçada sem rampa, lixo acumulado, banco quebrado) costumam ser relatados de forma dispersa: em conversas, grupos de mensagem ou de boca em boca. Assim, as prioridades não ficam claras e os moradores não sabem o que já foi visto e o que continua esperando.

**Público beneficiado.**
- Moradores, que podem registrar uma demanda e acompanhar sua situação;
- Associações de bairro e lideranças comunitárias, que precisam de uma visão organizada para cobrar e priorizar;
- Pessoas com deficiência, idosos e quem circula à noite, diretamente afetados por falhas de acessibilidade e iluminação.

> O sistema é um **protótipo**: não se integra a prefeituras nem promete o atendimento das demandas. Ele organiza informações para a própria comunidade.

---

## 3. Como executar

Requisito: Python 3.8 ou superior. Não é preciso instalar nada.

```bash
# a partir da raiz do repositório
python src/sistema.py           # menu interativo
python src/sistema.py --demo    # roteiro automático com todas as funcionalidades
python tests/teste_sistema.py   # 36 testes automáticos
```

### Estrutura do repositório

```
├── README.md
├── src/sistema.py          programa principal (comentado)
├── data/dados.csv          14 registros simulados (12 válidos + 2 inconsistentes)
├── data/historico.csv      10 eventos simulados de mudança de situação
├── tests/teste_sistema.py  testes automáticos simples
└── docs/
    ├── relatorio.pdf       relatório do projeto
    ├── link_video.txt      endereço do vídeo no YouTube
    └── uso_ia.md           como a IA foi usada e verificada
```

---

## 4. Dados: formato e regras

Os dados ficam em arquivos texto separados por **ponto e vírgula** (`;`), codificação UTF-8. O `;` foi escolhido porque as descrições podem conter vírgulas.

### `data/dados.csv`: ocorrências

| Campo | Obrigatório | Formato / valores aceitos |
|---|---|---|
| `id` | sim | 3 dígitos, único (ex.: `014`) |
| `categoria` | sim | `iluminacao`, `acessibilidade`, `limpeza`, `conservacao` |
| `descricao` | sim | até 120 caracteres, sem dados pessoais |
| `bairro` | sim | nome do bairro simulado |
| `local` | **não** | local genérico; se vazio, vira "Local não informado" |
| `dia_abertura` | sim | inteiro de 1 até o dia atual da simulação (dia 20) |
| `status` | sim | `aberta`, `em_analise`, `concluida` |

Categorias e situações usam **códigos padronizados** (minúsculos, sem acento). Na tela, aparecem com rótulos legíveis ("Iluminação", "Em análise").

### `data/historico.csv`: eventos de acompanhamento

`id;dia;status_anterior;status_novo;observacao`. São 10 eventos, em ordem cronológica, que explicam como cada ocorrência chegou à situação atual. Os eventos com `status_novo = concluida` fornecem o **dia de conclusão**, usado no indicador de tempo médio.

### Situações e seus significados

| Situação | Significado | Pode mudar para |
|---|---|---|
| **Aberta** | Registrada e aguardando triagem (está na fila) | Em análise |
| **Em análise** | Já examinada; está sendo verificada ou encaminhada | Concluída, ou Aberta (devolvida por falta de informação) |
| **Concluída** | Problema resolvido; sai das pendências | nenhuma (situação final) |

### Registros inconsistentes (de propósito)

| Linha | Problema | Tratamento |
|---|---|---|
| 14 (`013`) | categoria vazia | rejeitado: "campo obrigatório 'categoria' está vazio" |
| 15 (`005`) | código repetido **e** situação `resolvida` (desconhecida) | rejeitado com as duas mensagens |

Registros rejeitados **não entram** na lista nem nos indicadores e aparecem na opção 12 do menu. Os códigos deles **nunca são reaproveitados**. Por isso o próximo cadastro recebe o código `014`, e não `013`.

---

## 5. Estruturas de dados e justificativas

| Estrutura | Onde está | Para que serve | Por que esta escolha |
|---|---|---|---|
| **Lista** | `sistema["ocorrencias"]` | Guarda todas as ocorrências válidas, na ordem de registro | Permite percorrer tudo com `for` para listar, filtrar e calcular indicadores |
| **Dicionário** | `sistema["indice"]` (`id → ocorrência`) | Busca por código | Acesso direto pela chave (tabela *hash*), sem percorrer a lista inteira. A lista e o dicionário apontam para o **mesmo** objeto, então uma atualização vale nos dois |
| **Fila (FIFO)** | `sistema["fila"]` | Ocorrências **abertas** aguardando triagem | Quem registrou primeiro é examinado primeiro (justiça por ordem de chegada). `append` entra no fim e `pop(0)` sai do início. Ocorrência devolvida para "aberta" volta para o **fim** da fila |
| **Pilha (LIFO)** | `sistema["pilha"]` | Eventos de acompanhamento | O evento mais recente fica no topo; "ver últimos eventos" lê do topo para baixo sem remover nada |
| **Hierarquia (árvore)** | `montar_hierarquia()` → `{bairro: {categoria: [ids]}}` | Visão por bairro | Mostra **onde** cada tipo de problema se concentra. Uma liderança de bairro vê só o seu ramo da árvore |
| **Matriz** | `montar_matriz()` → lista de listas 4 × 3 | Quantidade por categoria × situação | Resume em uma tabela o cruzamento das duas classificações. Somas de linha e coluna conferem os totais |
| **Conjunto** | `sistema["ids_usados"]` | Códigos já lidos (inclusive rejeitados) | Evita reaproveitar códigos |

Algoritmos: **busca sequencial** com filtros (`filtrar`), **busca direta** por chave (`buscar_por_id`) e **ordenação por inserção** implementada manualmente (`ordenar_por_antiguidade`, opção 9 do menu) para listar as pendências mais antigas primeiro.

---

## 6. Regras lógicas

### Validação (`validar_registro`)
Usada tanto na leitura do arquivo quanto no cadastro. Um registro é recusado se:
1. algum campo obrigatório estiver vazio;
2. o código não tiver 3 dígitos ou já existir;
3. a categoria ou a situação não estiver entre os valores padronizados;
4. o dia de abertura não for inteiro ou estiver fora de 1 até o dia atual;
5. a descrição passar de 120 caracteres **ou** parecer ter dado pessoal (contém `@` ou 8 ou mais dígitos, como telefone ou CPF).

Todas as mensagens de erro de um registro são mostradas juntas, para a pessoa corrigir tudo de uma vez.

### Atualização de situação (`atualizar_status`)
Cadeia `if / elif / else`:
- `if novo is None`: a situação digitada não existe, então aparece "Situação desconhecida… Use: Aberta, Em análise, Concluída";
- `elif novo == atual`: nada muda, então aparece "já está…";
- `elif novo not in TRANSICOES[atual]`: a mudança pula etapas (aberta → concluída) ou reabre algo concluído, então o sistema recusa e informa quais mudanças são permitidas;
- `else`: aplica a mudança, grava o dia de conclusão (se for o caso), atualiza a fila e empilha o evento no histórico.

Antes disso, se o código não existe no dicionário, a mensagem é "Ocorrência 'XXX' não encontrada".

### Operadores AND, OR e NOT (exemplos no código)

| Função | Condição | Operadores |
|---|---|---|
| `eh_pendente` | `status == "aberta" or status == "em_analise"` | OR |
| `eh_atrasada` | `eh_pendente(oc) and not (dia_atual - dia_abertura <= 7)` | AND, NOT |
| `eh_prioritaria` | `eh_atrasada(oc) and (categoria == "iluminacao" or categoria == "acessibilidade")` | AND, OR |
| `filtrar` | `(categoria is None or oc_cat == categoria) and (status is None or oc_st == status)` | AND, OR |
| `validar_registro` | `codigo != "" and not (codigo.isdigit() and len(codigo) == 3)` | AND, NOT |
| `validar_registro` | `"@" in descricao or contar_digitos(descricao) >= 8` | OR |

### Expressão booleana documentada

Filtro usado na consulta (opção 3):

```
INCLUIR = (C_vazio OR categoria = C) AND (S_vazio OR status = S)
```

- `C_vazio` é verdadeiro quando o usuário não escolheu categoria (aperta Enter).
- Se a pessoa não escolhe categoria, o primeiro parêntese é sempre **verdadeiro**, e o filtro passa a depender só da situação, e vice-versa.
- Sem nenhum critério, os dois parênteses são verdadeiros, e todas as ocorrências aparecem.
- Exemplo: categoria = iluminação e status = aberta dá `(F OR V) AND (F OR V) = V` para a ocorrência 011, e `(F OR F) AND … = F` para a 003 (acessibilidade).

Tabela-verdade de um parêntese (`X_vazio OR campo = X`):

| X_vazio | campo = X | resultado |
|---|---|---|
| V | V | V |
| V | F | V |
| F | V | V |
| F | F | F |

Outra expressão usada nos indicadores é a de pendência **prioritária**: `P = A AND (I OR B)`, em que A = atrasada (> 7 dias e não concluída), I = iluminação e B = acessibilidade. Iluminação e acessibilidade afetam segurança e mobilidade, por isso entram na regra.

---

## 7. Indicadores

Todos calculados com laços e operações simples em `calcular_indicadores()`. Valores abaixo para os **dados originais** (dia simulado 20):

| Indicador | Fórmula | Resultado |
|---|---|---|
| Total válido | contagem da lista | 12 (14 lidos − 2 rejeitados) |
| Por categoria | `qtd_categoria / total × 100` | Iluminação 4 (33,3%) · Acessibilidade 3 (25,0%) · Limpeza 3 (25,0%) · Conservação 2 (16,7%) |
| Por situação | `qtd_situação / total × 100` | Aberta 5 (41,7%) · Em análise 4 (33,3%) · Concluída 3 (25,0%) |
| Pendências | `abertas + em análise` | 9 (75,0%) |
| Taxa de conclusão | `concluídas / total × 100` | 25,0% |
| Tempo médio até a conclusão | `Σ(dia_conclusão − dia_abertura) / nº concluídas` | (5 + 6 + 8) / 3 = **6,33 dias** |
| Espera média das pendências | `Σ(dia_atual − dia_abertura) / nº pendências` | 102 / 9 = **11,33 dias** |
| Pendências atrasadas | pendente **e** mais de 7 dias | 7 (002, 003, 005, 007, 008, 009, 010) |
| Atrasadas prioritárias | atrasada **e** (iluminação **ou** acessibilidade) | 4 (003, 005, 007, 008) |

Matriz categoria × situação:

|  | Aberta | Em análise | Concluída | Total |
|---|---|---|---|---|
| Iluminação | 1 | 2 | 1 | 4 |
| Acessibilidade | 3 | 0 | 0 | 3 |
| Limpeza | 0 | 2 | 1 | 3 |
| Conservação | 1 | 0 | 1 | 2 |
| **Total** | 5 | 4 | 3 | 12 |

### Interpretação

- **Iluminação** é a categoria mais registrada, e iluminação e acessibilidade empatam em pendências.
- **Nenhuma ocorrência de acessibilidade foi sequer analisada**: as 3 estão abertas. É o ponto mais preocupante do conjunto, porque afeta quem tem mobilidade reduzida.
- As pendências já esperam em média **11,33 dias**, quase o dobro do tempo que as demandas resolvidas levaram (6,33 dias). Isso sugere que a fila está crescendo mais rápido do que é atendida.
- **4 das 7 pendências atrasadas** são de iluminação ou acessibilidade e deveriam ir primeiro para a pauta da associação de moradores.
- Ressalva: são **12 registros fictícios**. Os números ilustram o funcionamento e não descrevem um bairro real.

O painel (opção 11) mostra os dados de origem, a fórmula de cada indicador, os resultados em tabela e barras de texto (`#`), e gera a interpretação automaticamente. Os valores mudam conforme cadastros e atualizações da sessão.

---

## 8. Exemplos de uso

### Cadastro (opção 4)
```
Novo código será: 014. Campos com * são obrigatórios.
Categoria*:  1 - Iluminação  2 - Acessibilidade  3 - Limpeza  4 - Conservação
> iluminação
Descrição breve* (sem dados pessoais): Refletor da praça apagado
Bairro* (digite o número ou um nome novo): 3          (Vila Aurora)
Local genérico (opcional, ex.: Praça Central): Praça Central
Dia de abertura (Enter = hoje, dia 20):
Ocorrência 014 cadastrada e colocada na fila de triagem.
```
Cadastro inválido (sem categoria):
```
Cadastro NÃO realizado. Corrija os itens abaixo:
   - campo obrigatório 'categoria' está vazio
```

### Consulta (opção 3): abertas de iluminação
```
Filtro: categoria = Iluminação; situação = Aberta
Código Categoria      Bairro            Local                 Situação    Dias
------------------------------------------------------------------------------
011    Iluminação     Jardim Primavera  Passarela de pedes... Aberta      5
014    Iluminação     Vila Aurora       Praça Central         Aberta      0
```

### Alteração de situação (opção 5)
```
[OK]   Ocorrência 014: Aberta -> Em análise (dia 20). Alteração registrada no histórico.
[ERRO] Mudança não permitida: Aberta -> Concluída. A partir de 'Aberta' é permitido: Em análise.
[ERRO] Mudança não permitida: Concluída -> Aberta. A partir de 'Concluída' é permitido: nenhuma (situação final).
[ERRO] Situação desconhecida: 'resolvida'. Use: Aberta, Em análise, Concluída.
Ocorrência '099' não encontrada.
```

### Eventos recentes (opção 8, topo da pilha)
```
dia 20 | ocorrência 014 | aberta -> em_analise | Atualização registrada pelo painel
dia 20 | ocorrência 014 | - -> aberta | Cadastro de nova ocorrência
dia 14 | ocorrência 010 | aberta -> em_analise | Limpeza do bueiro solicitada
```

### Hierarquia (opção 10)
```
Vila Aurora (5 ocorrências)
   +-- Iluminação (2): 001, 014
   +-- Acessibilidade (1): 003
   +-- Limpeza (1): 010
   +-- Conservação (1): 009
```

Para ver tudo em sequência: `python src/sistema.py --demo`.

---

## 9. Acessibilidade, inclusão e privacidade

**Acessibilidade e inclusão**
- Interface só em texto, compatível com leitores de tela. Nenhuma informação depende de cor: as barras `#` sempre vêm acompanhadas do número e do percentual.
- Entradas tolerantes: aceita maiúsculas ou minúsculas, com ou sem acento, o número da opção ou sinônimos ("luz", "concluido").
- Mensagens dizem **o que** deu errado e **como** corrigir, por exemplo listando as mudanças de situação permitidas.
- Uma opção de ajuda (14) explica categorias, situações e cuidados.
- Linguagem simples, sem termos técnicos na tela.
- Ctrl+C ou Ctrl+D encerram sem mensagens de erro.

**Privacidade**
- Todos os dados são **fictícios**. Não há nome, telefone, e-mail ou documento de moradores.
- Os locais são **genéricos** (praça, ponto de ônibus), sem endereço exato.
- A validação **recusa descrições** com `@` ou com 8 ou mais dígitos (padrão de telefone ou documento).
- Nada é enviado para a internet. As alterações ficam só na memória durante a sessão.

---

## 10. Testes

`python tests/teste_sistema.py` executa 36 verificações: carga e rejeição de registros, consistência do histórico, ordem da fila, indicadores (incluindo o tempo médio 19/3), normalização de entradas, cadastros válidos e inválidos (inclusive o de privacidade), filtros, transições permitidas e proibidas, pilha, ordenação e hierarquia.

---

## 11. Conclusões, limitações e aprendizados

**Conclusões.** Com estruturas simples, cada uma escolhida para uma finalidade (lista para percorrer, dicionário para achar, fila para atender por ordem, pilha para ver o recente, árvore para agrupar, matriz para resumir), dá para transformar relatos soltos em um painel que mostra o que está pendente, há quanto tempo e onde.

**Limitações**
- Dados simulados e poucos (12 registros). Os indicadores ilustram o método, não a realidade.
- As alterações **não são gravadas** no arquivo ao sair. Cada execução recomeça dos dados originais.
- O tempo é medido em "dias simulados" inteiros, não em datas reais.
- Não há controle de usuários nem verificação de que a demanda foi realmente resolvida.
- A detecção de dados pessoais é simples: pode deixar passar casos (um nome, por exemplo) ou bloquear descrições legítimas com muitos números.
- `pop(0)` em lista custa mais em filas muito grandes. Para este volume não faz diferença.

**Aprendizados**
- Escolher a estrutura certa simplifica o código: buscar pelo dicionário eliminou laços desnecessários.
- Centralizar a validação em uma função garantiu as mesmas regras na leitura do arquivo e no cadastro.
- Representar as mudanças de situação permitidas como um dicionário (`TRANSICOES`) deixou a regra visível e fácil de alterar.
- Dados inconsistentes de propósito ajudaram a testar o sistema como ele seria usado de verdade.

---

## 12. Uso de IA

Ver [`docs/uso_ia.md`](docs/uso_ia.md).
