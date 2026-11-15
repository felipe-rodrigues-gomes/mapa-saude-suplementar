# O "Painel Econômico-Financeiro da Saúde Suplementar" da ANS: o que aproveitar

Painel público da ANS (Power BI, DIOPE, 37 páginas, 1T2018–2T2026), olhado em 15/11/2026.
Fonte: **DIOPS**, os mesmos arquivos de `demonstracoes_contabeis` que o projeto já baixa, mais o SIB para o per capita.
**Diferente do SIP, aqui tudo é reproduzível por operadora com dado aberto.**

## O que a nota metodológica confirma

- **Sinistralidade** = (Eventos indenizáveis líquidos + |CCT|) ÷ (Contraprestações efetivas + |CCT|). É exatamente a fórmula a que chegamos testando variantes na etapa 2.
- O painel trabalha em três recortes: trimestre, acumulado no ano e 12 meses. É o mesmo desenho do `fato_contabil`.
- Para benchmark, usa **média agregada (ponderada) + mediana + Q1/Q3**, separados. A ficha da operadora deve seguir isso: "a sua operadora está no quartil X do seu porte".

## Duas armadilhas que a ANS documenta e que afetam o nosso cálculo

1. **Desde 2024, operadoras com até 20 mil beneficiários (segmento prudencial S4) não entregam o DIOPS do 1º ao 3º trimestre** (RN 527/2022). É por isso que ~200 operadoras só aparecem no 4T. Para elas, o 12 meses só existe no 4T. A ANS preenche os trimestres faltantes com uma regra (12m = saldo + 75%/50%/25% do 4T anterior). **Nós deixamos vazio**, sem estimar, e a nota metodológica do painel diz isso.
2. **Quebra de série em 2022 nos planos pós-estabelecidos** (RN 472 → RN 528). Até 2021 a receita era o valor cobrado do beneficiário; desde 2022 é só a taxa de administração, e o evento vem líquido da recuperação. O resultado não muda, mas receita e despesa encolhem. **Comparações de receita, despesa e per capita de 2021 com 2022 em diante não valem** para quem opera pós-estabelecido (muitas autogestões).

**Decisão (15/11/2026): resultado, índice combinado, despesas administrativa e de comercialização, resultado financeiro, forma de pagamento e despesas judiciais entram na v1.** Já estão no `fato_contabil` (acumulado, trimestre e 12 meses) e validados contra o painel da ANS (ver `02_tratamento.md`).

## O que trazer para o nosso painel (tudo dos arquivos que já temos)

| Indicador | Fórmula (ANS) | Por que vale |
|---|---|---|
| **Resultado líquido e operacional por operadora** | Líquido = contas 3 − 4 − 61; operacional = 31 + 33 + 34 + 37 − (41 + 43 + 44 + 46), já com o sinal de cada conta (32 e 34 vêm negativas) | "1 em cada 4 operadoras teve prejuízo" (no painel, 76% com lucro em 2026T2) |
| **Índice combinado** | (Eventos + \|CCT\| + Desp. adm. + Desp. comercialização) ÷ (Contrap. efetivas + \|CCT\| + Receitas adm.) | Didático: "de cada R$ 100 de mensalidade, R$ X vão para atendimento, administração e venda" |
| **Despesa administrativa (%)** e **comercialização (%)** | DA e DC da nota | Eficiência, comparável dentro do porte |
| **Resultado financeiro** | contas 35 − 45 | Mostra que boa parte do lucro vem das aplicações, não da operação |
| **Forma de pagamento à rede** | % dos eventos em 4111 (procedimento), 4112 (capitation), 4113 (orçamento global), 4114 (pacote), 4115 (rede própria), 4116 (rede indireta), 4117 (reembolso), 4118 (SUS) | Mostra o modelo de remuneração e a verticalização de cada operadora. Não existe pronto em lugar nenhum por operadora |
| **Despesas judiciais** | contas 411xxxx7 (eventos cobertos) e 4413x9x4 (não cobertos), em % dos eventos | Judicialização por operadora; casa com o ressarcimento suspenso na Justiça |
| **Quartis por porte** | P25 / mediana / P75 | Base da ficha da operadora |

Para a v2 (mais técnico, menos didático): liquidez corrente, prazo médio de pagamento de eventos (PMPE; casa com o tempo de pagamento do painel de glosa), provisões técnicas, ativos garantidores, créditos a receber.

## O que não trazer
- Árvores de balanço (ativo e passivo conta a conta).
- Valores deflacionados por modalidade de pagamento (pré × pós-estabelecido), que dependem da quebra de 2022.

## Problemas de experiência (o que evitar)
- 37 páginas com 6 a 7 filtros cada, iguais em todas.
- A ficha por operadora está escondida em "Indicadores anuais" (página 26) e "Lista de resultados" (página 11, tabela de 15 colunas).
- Gráficos com dez rótulos sobrepostos (série 12 meses).
- Rótulos de conta contábil ("33 - OUTRAS RECEITAS OPERACIONAIS") no lugar de perguntas.
