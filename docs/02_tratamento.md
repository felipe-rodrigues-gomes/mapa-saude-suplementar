# Etapa 2 — Tratamento e modelo de dados

Tudo é reproduzível: `scripts/` baixa da ANS e do IBGE e grava em `dados/tratados/` (parquet).

## Ordem de execução

```bash
python -I scripts/etl_beneficiarios.py .     # ~45 min: 20 meses de fim de trimestre, baixa, agrega e apaga o bruto
python -I scripts/etl_benef_municipio.py .   # ~10 min: 3 meses por município (mapa de cobertura)
python -I scripts/etl_contabil.py
python -I scripts/etl_qualidade.py           # IGR, IDSS, glosa
python -I scripts/etl_ressarcimento.py       # ~20 min
python -I scripts/etl_cadastro.py            # dim_operadora + fato_beneficiarios (depende dos anteriores)
python -I scripts/etl_ibge.py
python -I scripts/validar.py
```

## Tabelas

| Tabela | Grão | Período |
|---|---|---|
| `dim_operadora` | operadora (ativas + canceladas) | cadastro atual |
| `dim_municipio` | município IBGE, com população 2024–2026 | 2024–2026 |
| `fato_contabil` | operadora × trimestre; cada conta em acumulado no ano, trimestre isolado e 12 meses. Traz sinistralidade, resultados (líquido, operacional, financeiro, patrimonial), índice combinado, despesas administrativa e de comercialização, margem líquida, eventos por forma de pagamento e despesas judiciais | 2021T1–2026T2 |
| `fato_beneficiarios` | competência × operadora × UF × cobertura × contratação × faixa de reajuste × sexo | dez/2021–set/2026, fins de trimestre |
| `beneficiarios_municipio` | competência × município × cobertura | dez/2024, dez/2025, set/2026 |
| `fato_igr` | operadora × mês × cobertura | jan/2015–out/2026 |
| `fato_idss` | operadora × ano do IDSS (nota + 4 dimensões) | IDSS 2016–2025 |
| `fato_glosa` | operadora × semestre (5 indicadores + flags) | 2019S1–2025S2 |
| `fato_ressarc_uso` | mês do atendimento × operadora × UF do beneficiário × UF do hospital × tipo × especialidade | 2019–2025 |
| `fato_ressarc_cobranca` | mês do atendimento × operadora × status da análise × situação da cobrança | 2019–2025 |

## Decisões e por quê

**Sinistralidade no critério da ANS.** `(41 + |3117|) ÷ (31 + 32 + |3117|)`: eventos indenizáveis mais a corresponsabilidade cedida, sobre as contraprestações efetivas (receita de assistência menos tributos diretos) mais a corresponsabilidade cedida. Testei cinco variantes contra o número oficial; esta erra no máximo 0,4 p.p. Numerador e denominador ficam em colunas separadas para o Power BI somar antes de dividir (média de razões seria erro).

**12 meses móveis como série principal.** O 1º trimestre é sempre ~5 p.p. mais baixo; trimestre isolado mostra sazonalidade, não tendência. `12m(T) = acumulado(T) + ano anterior fechado − acumulado(T do ano anterior)`.

**Segmento pela carteira, não pela modalidade.** Médico-hospitalar = tem beneficiário médico-hospitalar no SIB. Sem carteira: segmentação do painel de glosa, depois modalidade.

**Porte como a ANS.** Vínculos ativos totais (médico + odonto): pequeno < 20 mil, médio 20–100 mil, grande > 100 mil.

**Faixa de reajuste para "59+".** A faixa etária comum pula de 55–59 para 60–64; a de reajuste tem "59 anos ou mais".

**Cobertura só de 2024 em diante.** Ver `etl_ibge.py`: as estimativas do IBGE antes e depois do Censo 2022 não são comparáveis.

**Glosa: marcar, não apagar.** Glosa inicial < 0,05% ou ≥ 50% recebe `FLAG_GLOSA_EXTREMA` (provável falha de envio ao TISS); glosa final maior que a inicial recebe `FLAG_GLOSA_FINAL_MAIOR`. A base só traz percentuais: média de mercado só por mediana ou ponderada por despesa assistencial.

**Ressarcimento ao SUS: uso do SUS não é, por si só, falha da operadora.** Cada atendimento recebe um motivo provável e um de três grupos de leitura (regra em `etl_ressarcimento.py::classificar`, validada em 15/11/2026; a primeira regra que bate vale):

| Grupo | Motivos | Por quê |
|---|---|---|
| Não indica falha | transplante (grupo SIGTAP 05) · trauma e causas externas (0308, CID S–Y) · fora da cobertura do plano (internação em plano ambulatorial, APAC em plano só hospitalar) | Fila nacional única; o SAMU leva ao pronto-socorro de referência; o plano não cobre |
| Provável falha de acesso | parto e obstetrícia (0310, 0411, CID O) · psiquiatria (especialidade, CID F) · cirurgia programável (0401, 0404, 0407–0410, 0412–0415) | Procedimento coberto e, em regra, agendável: ir ao SUS sugere rede insuficiente, demora ou coparticipação pesada |
| Zona cinzenta | oncologia (0304, 0416, CID C/D0–D4) · diálise (0305, 0418) · olhos (0405) · cardiovascular (0406) · medicamento de alto custo (06) · diagnóstico de alta complexidade (02) · internação clínica · outros | Continuidade de tratamento iniciado no SUS, centros públicos de referência, rede privada escassa no interior: o dado não separa escolha de falha |

Resultado (2019–2025, 3,9 mi de atendimentos): **não indica falha 11,6% · provável falha de acesso 18,0% · zona cinzenta 70,4%** (em valor: 9,0% · 17,2% · 73,8%). Maiores motivos: oncologia 32%, internação clínica 13%, diálise 12% (26% do valor), cirurgia programável 9%, parto 7%.

**Quebra de série em 2024:** as APACs de acompanhamento pós-transplante caem de ~45 mil/ano (2019–2022) para ~1,9 mil (2024), mudança no que a ANS identifica e cobra, não no comportamento. Por isso "não indica falha" cai de ~14% para ~7%. Na série histórica, transplante fica fora ou com aviso; a comparação entre operadoras dentro do mesmo ano não é afetada. 2025 ainda está incompleto (a identificação leva meses).

Limites: o arquivo não informa se o atendimento foi de urgência nem se o plano cobre obstetrícia; na dúvida o caso fica na zona cinzenta. A ANS só cruza internações (AIH) e alta complexidade ambulatorial (APAC): consulta, exame simples e pronto-socorro sem internação ficam de fora.

## Validação (scripts/validar.py, 15/11/2026)

| Checagem | Resultado |
|---|---|
| Sinistralidade médico-hospitalar × número oficial da ANS | 2024: 83,66% × 83,8% · 1S25: 81,47% × 81,1% · 2025: 81,76% × 81,7% · 1S26: 81,93% × 81,9% (máx. 0,37 p.p.) |
| Fórmula × nota metodológica do Painel Econômico-Financeiro da ANS | idêntica |
| Lucro líquido médico-hospitalar × ANS | 2024: R$ 10,26 × 10,2 bi · 2025: R$ 23,39 × 23,4 bi · 1S26: R$ 10,86 × 10,89 bi |
| Resultado operacional 2025 × ANS | R$ 9,73 × 9,8 bi |
| Operadoras com lucro, 1S26 | 75,8% (painel da ANS: ~76%) |
| Despesas judiciais 12m até 2026T2 | R$ 5,13 bi, 1,8% dos eventos (painel da ANS: ~R$ 5,2 bi, ~1,8%) |
| Eventos por forma de pagamento, 1S26 | procedimento 58,9% · pacote 13,1% · rede própria 12,9% · rede indireta 8,2% · reembolso 3,4% · capitation 1,0% · orçamento global 1,1% |
| Beneficiários por operadora × denominador do IGR (set/2026) | 99,8% das 663 operadoras com diferença < 1% |
| Total de beneficiários set/2026 | 53,1 mi médico-hospitalares, 37,4 mi odontológicos |
| Cobertura dos indicadores (médico-hospitalares com contábil em 2026T2, em % da receita) | beneficiários 100% · IGR 100% · IDSS 2025 97,1% · glosa 2025S2 99,5% (85,9% sem flag) |
| Receita e custo por vida/mês, mercado, 12m até 2026T2 | R$ 566 de receita, R$ 462 de custo |
| Cobertura de plano médico, set/2026 ÷ população IBGE 2026 | Brasil 24,8% · SP 40,5% · ES 34,2% · DF 34,0% · CE 16,0% · RR 4,2%; nenhum município acima de 100% |
| Vidas sem município válido | 49,6 mil (0,09%), informadas só com código da UF |

**Valores que não podem ir para ranking sem regra** (a definir na etapa 3):
- Sinistralidade negativa ou acima de 150% em 9 operadoras (denominador minúsculo, carteira em extinção, autogestão com patrocinador cobrindo o déficit, veículos societários com receita e evento separados).
- Receita por vida absurda (máx. R$ 106 mi/vida/mês) em operadoras com pouquíssimas vidas médicas e receita grande.
- Proposta: entra no ranking só operadora com ≥ 1.000 vidas médico-hospitalares e receita 12m > 0; fora disso aparece na ficha com aviso, sem posição.

## Problemas encontrados nos dados da ANS

1. **Taxa de cobertura (base 047):** população zerada em quase todas as linhas (soma 604 mil para o Brasil) e municípios de Tocantins sob GO. Substituída pelo IBGE.
2. **Acentos corrompidos:** parte dos arquivos de beneficiários vem com "M�dico-hospitalar" na origem e outros em UTF-8 lido como latin-1 ("MÃ©dico"). A classificação usa só os trechos sem acento.
3. **Contábeis 1T–3T de 2021 sem saldo inicial:** o trimestre isolado sai da diferença dos acumulados.
4. **Saldo inicial ≠ saldo final anterior em ~10% das operadoras** (reenvios). Por isso o 12 meses usa só saldos finais.
5. **IGR:** o dicionário diz que `QTD_BENEFICIARIOS` é "quem reclamou", mas é a carteira. Em 2015–2018 o IGR vem arredondado a uma casa.
6. **~200 operadoras só entregam o 4º trimestre.** Desde 2024 as operadoras com até 20 mil beneficiários (segmento S4) estão dispensadas do DIOPS do 1º ao 3º trimestre (RN 527/2022). Somam 0,26% da receita. Para elas o 12 meses só existe no 4T; a ANS estima os trimestres faltantes, nós deixamos vazio.
7. **Quebra de série em 2022 nos planos pós-estabelecidos** (RN 472/528): a receita passou a ser só a taxa de administração. Receita e despesa de 2021 não se comparam com as de 2022 em diante para essas operadoras; a sinistralidade quase não muda.
