# Etapa 1 — Mapa das fontes (dados abertos ANS)

Levantamento feito em 15/11/2026 em `https://dadosabertos.ans.gov.br/FTP/PDA/`.

## Bases da v1

| Tema | Pasta no portal | Grão | Período disponível | Última carga | Defasagem | Volume |
|---|---|---|---|---|---|---|
| Sinistralidade (DIOPS) | `demonstracoes_contabeis/{ano}/{n}T{ano}.zip` | operadora × conta contábil × trimestre | 2001 → 2T2026 | 16/09/2026 | ~2,5 meses | ~9 MB/trimestre |
| Beneficiários | `informacoes_consolidadas_de_beneficiarios-024/{AAAAMM}/pda-024-icb-{UF}-{AAAA_MM}.zip` | operadora × UF × município × sexo × faixa × plano × contratação | 2021-05 → 2026-09 | 05/11/2026 | ~1,5 mês | ~400 MB/mês (zip) |
| Reclamações (IGR) | `IGR/IGR_versao_2023/pda-023-igr.csv` | operadora × cobertura × mês | 2015-01 → 2026-10 | 09/11/2026 | ~1 mês | 17 MB |
| IDSS | `historico_idss-020/pda-020-historico-idss-2016_2025.csv` | operadora × ano (IDSS + 4 dimensões) | IDSS 2016 → IDSS 2025 (ano-base 2024) | 23/06/2026 | ~1,5 ano | 0,8 MB |
| Glosa | `painel_de_glosas-057/dados/*.csv` | operadora × semestre | 2019-1 → 2025-2 | 20/07/2026 | ~7 meses | 5 × 1,8 MB |
| Cadastro | `operadoras_de_plano_de_saude_{ativas,canceladas}/` | operadora | atual | 11/11/2026 | — | 1,3 MB |

Fora da v1: NIP bruta (`demandas_dos_consumidores_nip`, 162 MB só 2026; o IGR já agrega a NIP) e TISS (`TISS/HOSPITALAR|AMBULATORIAL/{ano}/{UF}`, 2015–2025).

## Colunas que importam

- **Contábeis:** `DATA` (início do trimestre), `REG_ANS`, `CD_CONTA_CONTABIL`, `DESCRICAO`, `VL_SALDO_INICIAL`, `VL_SALDO_FINAL` (vírgula decimal).
- **Beneficiários:** `ID_CMPT_MOVEL`, `CD_OPERADORA`, `MODALIDADE_OPERADORA`, `SG_UF` (UF de residência), `TP_SEXO`, `DE_FAIXA_ETARIA`, `DE_FAIXA_ETARIA_REAJ` (tem "59 anos ou mais"), `DE_CONTRATACAO_PLANO`, `COBERTURA_ASSIST_PLAN`, `QT_BENEFICIARIO_ATIVO/ADERIDO/CANCELADO`.
- **IGR:** `IGR` (reclamações por 100 mil beneficiários), `QTD_RECLAMACOES`, `QTD_BENEFICIARIOS` (é a carteira, não "quem reclamou" como diz o dicionário), `PORTE_OPERADORA`, `COMPETENCIA`, `COBERTURA`.
- **IDSS:** `IDSS_{ano}_{ano-base}` + `IDQS`, `IDGA`, `IDSM`, `IDGR`; "ND" = não disponível.
- **Glosa:** `PC_GLOSA_INCIAL` (sic), `PC_GLOSA_FINAL`, `QT_TEMPO_PAGAMENTO`, `PC_NUMERO_GUIAS_SEM_RETORNO`, `PC_VALOR_GUIAS_SEM_RETORNO`, `CD_PERIODO` (AAAA-01/02), `DE_PORTE_OPERADORA`, `NM_SEGMENTACAO_OPERADORA`.

## Checagens feitas

### Sinistralidade — fórmula conferida contra a ANS

| Período | ANS oficial | 41 ÷ 311 | **41 ÷ (311 + 312)** |
|---|---|---|---|
| 2024 | 83,8% | 83,5% | **83,5%** |
| 2025 | 81,7% | 81,0% | **81,1%** |
| 1S2025 | 81,1% | 80,6% | **80,9%** |
| 1S2026 | 81,9% | 79,9% | **81,4%** |

Recorte: médico-hospitalares (sem odontológicas e administradoras). A conta 312 (variação das provisões técnicas) é o que separa "contraprestações líquidas" de "contraprestações efetivas"; em 2026 ela ficou em −R$ 3,3 bi e sem ela o erro chega a 2 p.p. Sobra 0,2–0,6 p.p., provavelmente porque a ANS classifica "médico-hospitalar" pela segmentação e não pela modalidade (fechar na etapa 2 usando `NM_SEGMENTACAO_OPERADORA`).

### Saldos acumulados no ano
`VL_SALDO_FINAL` das contas de resultado é acumulado de janeiro até o fim do trimestre. Trimestre isolado = final − inicial. Em ~10% das operadoras o saldo inicial do trimestre não bate com o saldo final do arquivo anterior (retificação), então o trimestre isolado é ruidoso.

### Sazonalidade
O 1º trimestre é sempre ~4–5 p.p. mais baixo (77,4% no 1T25 contra 82,1% no 2T25 isolado, mercado todo, fórmula 41 ÷ 311). Comparar trimestres isolados engana.

### Operadoras só no 4T
~200 operadoras só entregam o 4T (as que têm receita: 137, sendo 129 odontológicas, ou 0,26% da receita). Não afetam o recorte médico-hospitalar, mas o "trimestre isolado" do 4T delas vale pelo ano todo.

### Cobertura
- Contábeis: ~700 operadoras com receita por trimestre (2T2026 completo: 781 arquivos contra 783 no 2T2025).
- Glosa 2025-2: 638 médico-hospitalares; mediana 2,3%, p90 11,4%, máx. 100%.
- IDSS 2025: 803 operadoras com nota.
- IGR: ~884 operadoras por mês.
- Beneficiários CE 2026-09: 1,49 mi médico-hospitalares, 458 operadoras.
