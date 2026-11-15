# Etapa 3 — Indicadores e achados

Base: `ind_operadora.parquet` (scripts/indicadores.py) e explorações em `scripts/explorar.py [mercado|serie|qualidade|sus|uf]`.
Recorte: operadoras médico-hospitalares; ranking = ativas, ≥ 1.000 vidas médicas, receita 12m > 0, sinistralidade entre 30% e 150%.
**546 operadoras no ranking = 95% das vidas e 99% da receita.** Quem fica fora aparece na ficha com o motivo (cancelada, sem balanço recente, só balanço anual, sinistralidade atípica etc.).

## Achados conferidos

### 1. Em cinco anos, a operação de planos médicos deu prejuízo; o lucro veio das aplicações ⭐ candidato a gancho
| Ano | Resultado da operação | Resultado financeiro | Lucro líquido |
|---|---|---|---|
| 2021 | −R$ 0,9 bi | R$ 4,5 bi | R$ 2,6 bi |
| 2022 | −R$ 10,7 bi | R$ 9,4 bi | −R$ 0,5 bi |
| 2023 | −R$ 6,0 bi | R$ 11,1 bi | R$ 1,9 bi |
| 2024 | R$ 4,2 bi | R$ 8,4 bi | R$ 10,3 bi |
| 2025 | R$ 9,7 bi | R$ 14,6 bi | R$ 23,4 bi |
| **Soma** | **−R$ 3,6 bi** | **R$ 48,1 bi** | **R$ 37,6 bi** |

Conferido com a ANS: 2022 operacional −10,7 (revisado) e financeiro 9,4; 2023 −5,9 e 11,2; 2025 9,8 e lucro 23,4.
Leitura justa: aplicar as reservas obrigatórias faz parte do negócio, e a operação voltou ao azul em 2024–2025. Mesmo em 2025, o financeiro rendeu 1,5× o operacional.

### 2. 1 em cada 5 operadoras só fecha no azul por causa das aplicações
12 meses até jun/2026: 212 de 546 (39%) têm prejuízo na operação; 110 delas (20% do total) terminam com lucro graças ao resultado financeiro. Nas pequenas, 46% perdem na operação.

### 3. O lucro é concentrado
As 3 maiores lucratividades (Amil, Bradesco Saúde, SulAmérica) somam 41,5% de todo o lucro positivo do setor. Medicina de grupo tem a maior margem agregada (7,9%) e, ao mesmo tempo, a maior fração de operadoras no prejuízo (34%).

### 4. Plano individual encolhe, carteira envelhece
dez/2021 → set/2026: empresarial +5,0 mi de vidas; individual −573 mil; adesão −569 mil. Individual caiu de 18,0% para 15,6% da carteira. 59 anos ou mais: de 15,4% para 16,6% (+925 mil só no empresarial).

### 5. Gastar mais com o cliente não reduz reclamação
Correlação (Spearman) entre sinistralidade e reclamações: 0,03. Em vidas, 44% dos clientes de médias e grandes estão em operadoras com sinistralidade abaixo e reclamação acima da mediana do porte; medicina de grupo concentra esse quadrante.

### 6. A nota de qualidade da ANS quase não acompanha a reclamação do cliente
Mesmo ano (IDSS 2025, ano-base 2024 × IGR 2024), operadoras com ≥ 20 mil vidas: IDSS × IGR = −0,11. Só a dimensão de regulação (IDGR, que já usa as reclamações) acompanha (−0,46); a de acesso (IDGA) não (−0,03). Bom para a ficha e para a nota metodológica; fraco como gancho.

### 7. Uso do SUS, controlando pelo estado
Razão observado ÷ esperado para os estados onde cada uma atua (atendimentos de 2024): medicina de grupo 1,41 (provável falha de acesso: 1,47); filantropia 1,17; autogestão 0,87; cooperativa 0,80; seguradora 0,45. Entre as grandes, as entidades com "Hapvida" no nome ficam entre 1,7 e 2,3 (falha de acesso 1,7 a 2,5).

### 8. Ressarcimento ao SUS parado na Justiça é concentrado
R$ 985 mi suspensos judicialmente de R$ 4,99 bi cobrados (atendimentos de 2019–2025). As 5 primeiras operadoras somam 87%; as 10 primeiras, 94,5%. Só 94 de 772 operadoras cobradas têm algum valor suspenso. A maior sozinha: R$ 491 mi (73% do que lhe foi cobrado).

### 9. Mercados regionais concentrados
Ceará: uma operadora tem 47,7% das vidas médicas (HHI 2.902); Amazonas: 51,7% (HHI 3.217). Pelo critério usado na defesa da concorrência, acima de 2.500 é mercado altamente concentrado. No Nordeste, operadoras com "Hapvida" no nome têm 31% das vidas. No outro extremo: SP, SC e DF abaixo de 600.
Cobertura: Brasil 24,8%; CE 16,0%; crescimento de vidas no CE desde dez/2021: +13,5% (Brasil +7,8%).

## Ressalvas que vão para o painel
- Agrupamento por grupo econômico **não existe no dado da ANS**; "Hapvida" acima é filtro por nome do registro, não grupo societário. O painel mostra por registro ANS.
- SUS: taxa por mil vidas com controle por UF (padronização indireta); não separa urgência; transplante tem quebra de série em 2024.
- IGR de operadora com menos de 20 mil vidas oscila demais: fica fora dos quadrantes.
- Glosa: 99,1% de glosa inicial na Bradesco Saúde e 0,4% na Prevent Senior são falhas de envio (flag), fora do ranking de glosa.

## Gancho do post — DECIDIDO (15/11/2026): achado 1, "o lucro vem das aplicações"

## Recomendação de gancho do post
**Achado 1**: conferido contra a ANS ano a ano, fala do mercado inteiro (não acusa ninguém) e surpreende quem acha que "plano de saúde dá muito lucro". Frase-base:
> "Em 5 anos, as operadoras de planos médicos perderam R$ 3,6 bilhões vendendo plano de saúde — e ganharam R$ 48 bilhões aplicando dinheiro."

Alternativas: achado 9 (para o público do Nordeste), achado 2 (mais leve), achado 8 (forte, mas aponta um nome e pede cuidado jurídico e de tom).
