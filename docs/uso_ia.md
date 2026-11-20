# Uso de Inteligência Artificial

**Autor:** Thiago Henrique Campos de Souza Giuliani · RM576080

Usei um assistente de IA (Claude, da Anthropic) no desenvolvimento deste projeto, como o enunciado da Global Solution permite. Abaixo descrevo onde a IA participou e como verifiquei o resultado.

## Onde houve apoio

| Etapa | Como a IA ajudou | Como verifiquei |
|---|---|---|
| Planejamento | Propôs quais estruturas usar em cada requisito (lista, fila, pilha, dicionário, hierarquia e matriz) e as regras de mudança de situação | Comparei cada escolha com os requisitos do enunciado e com os conteúdos das fases 1 a 3 |
| Dados fictícios | Gerou as 14 ocorrências e os 10 eventos de histórico, incluindo os 2 registros inconsistentes | Conferi que não há dado pessoal nem endereço real e que os totais batem com o exemplo do enunciado (5 abertas, 4 em análise e 3 concluídas) |
| Código | Gerou o `src/sistema.py` e os testes em `tests/teste_sistema.py` | Executei o menu e o modo `--demo`, testei entradas válidas e inválidas, rodei os testes e conferi os cálculos à mão (por exemplo, tempo médio = (5 + 6 + 8) / 3 = 6,33 dias) |
| Documentação | Redigiu o README e o relatório | Conferi que os exemplos e os números dos documentos são os mesmos que o programa imprime |
| Vídeo | Gerou o vídeo de apresentação (telas com o programa rodando e textos explicativos, sem narração) | Assisti ao vídeo e conferi que as telas mostram a saída real do programa |

## Minha parte

- Revisão e entendimento do código: sei explicar o papel de cada estrutura e de cada função principal.
- Testes manuais no terminal.
- Publicação do repositório e entrega na plataforma.

## Cuidados

- Nenhum dado pessoal real foi fornecido à IA.
- O código usa apenas Python básico (sem pandas, numpy ou outras bibliotecas externas), dentro do que foi estudado nas fases 1 a 3.
