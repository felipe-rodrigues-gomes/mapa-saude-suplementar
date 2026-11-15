"""Gera o projeto Power BI (PBIP: modelo em TMDL + relatório em PBIR) em powerbi/.

O modelo lê os parquet de dados/pbi pelo parâmetro PastaDados.
DAX nos arquivos usa a sintaxe invariante (vírgula), que é como o Power BI grava;
no Desktop em PT-BR as mesmas fórmulas aparecem com ponto e vírgula.
Uso: python -I scripts/gerar_pbip.py            (recria o modelo; não mexe nas páginas existentes)
"""
import json, shutil, sys, uuid, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import RAIZ
import pyarrow.parquet as pq

NOME = "MapaSaudeSuplementar"
PASTA = RAIZ / "powerbi"
SM = PASTA / f"{NOME}.SemanticModel"
RP = PASTA / f"{NOME}.Report"
DADOS = RAIZ / "dados" / "pbi"
NS = uuid.UUID("6f1d2c3a-0000-4000-8000-000000000001")


def tag(*partes):
    return str(uuid.uuid5(NS, "/".join(partes)))


def q(nome):
    """Nome de objeto TMDL: entre aspas simples se tiver espaço ou símbolo."""
    return nome if nome.replace("_", "").isalnum() else "'" + nome.replace("'", "''") + "'"


TIPO = {"string": "string", "int64": "int64", "double": "double", "bool": "boolean", "timestamp[us]": "dateTime"}

TABELAS = {  # tabela: (descrição, colunas ocultas por prefixo, ordenações {coluna: coluna_de_ordem})
    "dOperadora": ("Operadoras médico-hospitalares: cadastro da ANS e foto atual dos indicadores (ind_operadora).", (), {}),
    "dTrimestre": ("Trimestres do DIOPS (2021T1 em diante).", (), {"ROTULO": "ORDEM", "ROTULO_CURTO": "ORDEM"}),
    "dCompetencia": ("Meses da carteira (fins de trimestre) e do IGR.", (), {"ROTULO": "COMPETENCIA"}),
    "dIndicador": ("Tabela desconectada: um indicador por linha, para a ficha da operadora.", (), {"INDICADOR": "ORDEM"}),
    "dFormaPagamento": ("Tabela desconectada: formas de pagamento à rede, para o gráfico da ficha.", (), {"FORMA": "ORDEM"}),
    "fContabil": ("DIOPS por operadora e trimestre: acumulado no ano (_ytd) e 12 meses (_12m).", ("sinist_", "comb_", "ev_", "jud_", "desp_", "contraprest_", "resultado_"), {}),
    "fCarteira": ("Vidas médico-hospitalares por competência, operadora, contratação e faixa de reajuste.", (), {}),
    "fIGR": ("Reclamações (NIP) e beneficiários da assistência médica por operadora e mês.", (), {}),
}

RELACOES = [("fContabil", "REG", "dOperadora", "REG"), ("fContabil", "PERIODO", "dTrimestre", "PERIODO"),
            ("fCarteira", "REG", "dOperadora", "REG"), ("fCarteira", "COMPETENCIA", "dCompetencia", "COMPETENCIA"),
            ("fIGR", "REG", "dOperadora", "REG"), ("fIGR", "COMPETENCIA", "dCompetencia", "COMPETENCIA")]

# ---------------------------------------------------------------- medidas
# (tabela, pasta, nome, expressão DAX, formato, descrição)
M = []


def medida(tabela, pasta, nome, dax, fmt=None, desc="", fmt_dinamico=None):
    M.append(dict(tabela=tabela, pasta=pasta, nome=nome, dax=dax.strip("\n"), fmt=fmt, desc=desc, fmt_din=fmt_dinamico))


# --- Sinistralidade e índices (fContabil)
medida("fContabil", "1. Sinistralidade", "Sinistralidade (12 meses)",
       "DIVIDE ( SUM ( fContabil[sinist_num_12m] ), SUM ( fContabil[sinist_den_12m] ) )", "0.0%",
       "Quanto da mensalidade volta em atendimento. (eventos + |corresponsabilidade cedida|) ÷ (contraprestações efetivas + |corresponsabilidade cedida|), 12 meses. Soma numerador e denominador antes de dividir: é a média ponderada pela receita.")
medida("fContabil", "1. Sinistralidade", "Sinistralidade (no ano)",
       "DIVIDE ( SUM ( fContabil[sinist_num_ytd] ), SUM ( fContabil[sinist_den_ytd] ) )", "0.0%",
       "Mesma fórmula, acumulada de janeiro até o trimestre. É o número que a ANS divulga.")
medida("fContabil", "1. Sinistralidade", "Índice combinado (12 meses)",
       "DIVIDE ( SUM ( fContabil[comb_num_12m] ), SUM ( fContabil[comb_den_12m] ) )", "0.0%",
       "(eventos + |CCT| + despesas administrativas + comercialização) ÷ (contraprestações efetivas + |CCT| + receitas administrativas). Acima de 100%, a operação do plano dá prejuízo.")

# --- Resultado (gancho)
for nome, col, desc in [("Resultado da operação", "resultado_operacional", "Receitas menos despesas da operação de saúde (contas 31+32+33+34+37 − 41−43−44−46)."),
                        ("Resultado das aplicações", "resultado_financeiro", "Receitas menos despesas financeiras (contas 35 − 45)."),
                        ("Lucro líquido", "resultado_liquido", "Receitas − despesas − impostos e participações (contas 3 − 4 − 61).")]:
    medida("fContabil", "2. Resultado", f"{nome} (R$ bi)",
           f"DIVIDE ( CALCULATE ( SUM ( fContabil[{col}_ytd] ), dTrimestre[FIM_DE_ANO] = TRUE () ), 1E9 )", "#,0.0",
           desc + " Ano fechado: usa o acumulado do 4º trimestre.")
    medida("fContabil", "2. Resultado", f"{nome} 2021–2025 (R$ bi)",
           f"CALCULATE ( [{nome} (R$ bi)], dTrimestre[ANO] >= 2021, dTrimestre[ANO] <= 2025 )", "#,0.0",
           "Soma dos cinco anos fechados.")
medida("fContabil", "2. Resultado", "Lucro líquido 12 meses (R$ mi)",
       "DIVIDE ( SUM ( fContabil[resultado_liquido_12m] ), 1E6 )", "#,0.0")
medida("fContabil", "2. Resultado", "Aplicações ÷ operação (ano)",
       "DIVIDE ( [Resultado das aplicações (R$ bi)], [Resultado da operação (R$ bi)] )", "0.0x",
       "Quantas vezes as aplicações renderam o que a operação rendeu.")

# --- Rede e judicial
for k, rot in [("procedimento", "por procedimento"), ("pacote", "em pacote"), ("rede_propria", "em rede própria"),
               ("rede_indireta", "em rede indireta"), ("capitation", "por capitation"),
               ("orcamento_global", "por orçamento global"), ("reembolso", "por reembolso")]:
    medida("fContabil", "3. Como paga a rede", f"% dos eventos {rot}",
           f"DIVIDE ( SUM ( fContabil[ev_{k}_12m] ), SUM ( fContabil[ev_conhecidos_12m] ) )", "0.0%",
           "Eventos conhecidos ou avisados, 12 meses, por forma de pagamento (contas 4111 a 4119).")
ramos_fp = "\n".join(f'        "{k}", DIVIDE ( SUM ( fContabil[ev_{k}_12m] ), SUM ( fContabil[ev_conhecidos_12m] ) ),'
                     for k in ["procedimento", "pacote", "rede_propria", "rede_indireta", "reembolso", "capitation", "orcamento_global"])
medida("dFormaPagamento", "3. Como paga a rede", "% dos eventos (forma de pagamento)",
       f"""
VAR _forma = SELECTEDVALUE ( dFormaPagamento[CODIGO] )
RETURN
    SWITCH (
        _forma,
{ramos_fp.rstrip(',')}
    )""", "0%", "Parte dos eventos conhecidos ou avisados paga na forma da linha (contas 4111 a 4119 do DIOPS), 12 meses.")
medida("fContabil", "3. Como paga a rede", "Despesa judicial (% dos eventos)",
       "DIVIDE ( SUM ( fContabil[jud_total_12m] ), SUM ( fContabil[desp_assist_12m] ) )", "0.00%",
       "Despesas judiciais com eventos cobertos (411xxxx7) e não cobertos (4413x9x4) ÷ eventos indenizáveis, 12 meses.")

# --- Operadoras (dOperadora, foto atual)
medida("dOperadora", "4. Operadoras", "Operadoras no ranking",
       "CALCULATE ( COUNTROWS ( dOperadora ), dOperadora[RANKING_OK] = TRUE () )", "#,0",
       "Ativas, ≥ 1.000 vidas médicas, receita nos últimos 12 meses e sinistralidade entre 30% e 150%.")
for nome, cond, desc in [
        ("% com prejuízo na operação", "dOperadora[resultado_operacional] < 0", "Resultado da operação negativo nos 12 meses até jun/2026."),
        ("% com prejuízo no fim", "dOperadora[resultado_liquido] < 0", "Lucro líquido negativo nos 12 meses até jun/2026."),
        ("% salvas pelas aplicações", "dOperadora[resultado_operacional] < 0 && dOperadora[resultado_liquido] > 0",
         "Prejuízo na operação, mas lucro no fim graças ao resultado financeiro.")]:
    medida("dOperadora", "4. Operadoras", nome,
           f"""
VAR _ranking = FILTER ( dOperadora, dOperadora[RANKING_OK] = TRUE () )
RETURN
    DIVIDE ( COUNTROWS ( FILTER ( _ranking, {cond} ) ), COUNTROWS ( _ranking ) )""", "0.0%", desc + " Só operadoras do ranking.")
medida("dOperadora", "5. Ficha", "Operadora escolhida",
       'SELECTEDVALUE ( dOperadora[NOME_EXIBICAO], "Escolha uma operadora" )')
medida("dOperadora", "5. Ficha", "Perfil da operadora",
       """
IF (
    HASONEVALUE ( dOperadora[REG] ),
    SELECTEDVALUE ( dOperadora[MODALIDADE] ) & " · porte " & LOWER ( SELECTEDVALUE ( dOperadora[PORTE] ) )
        & " · registro ANS " & SELECTEDVALUE ( dOperadora[REG] ) & " · sede " & SELECTEDVALUE ( dOperadora[UF_SEDE] )
)""")
medida("dOperadora", "5. Ficha", "Aviso de ranking",
       """
VAR _motivo = SELECTEDVALUE ( dOperadora[MOTIVO_FORA_RANKING] )
RETURN
    IF (
        HASONEVALUE ( dOperadora[REG] ),
        IF ( ISBLANK ( _motivo ), "Comparada com as operadoras do mesmo porte.", "Fora do ranking: " & _motivo & ". Os números aparecem, sem comparação." )
    )""")

# --- Ficha: um SWITCH por indicador (dIndicador desconectada)
CODIGOS = ["sinistralidade", "indice_combinado", "margem_liquida", "indice_desp_adm", "receita_vida_mes",
           "custo_vida_mes", "cresc_vidas_12m", "pct_59mais", "igr_12m", "idss", "glosa_inicial",
           "tempo_pagamento_dias", "sus_falha_por_mil", "sus_pct_justica", "pct_judicial", "pct_ev_rede_propria"]


def filtro_extra(c):
    if c == "glosa_inicial":
        return " && NOT dOperadora[flag_glosa]"
    if c == "igr_12m":
        return " && dOperadora[vidas_mh] >= 20000"
    return ""


valor = "\n".join(f'            "{c}", MAX ( dOperadora[{c}] ),' for c in CODIGOS if c != "glosa_inicial")
medida("dIndicador", "5. Ficha", "Valor da operadora",
       f"""
VAR _codigo = SELECTEDVALUE ( dIndicador[CODIGO] )
RETURN
    IF (
        HASONEVALUE ( dOperadora[REG] ),
        SWITCH (
            _codigo,
{valor}
            "glosa_inicial", IF ( SELECTEDVALUE ( dOperadora[flag_glosa] ), BLANK (), MAX ( dOperadora[glosa_inicial] ) )
        )
    )""", desc="Valor do indicador da linha para a operadora escolhida. Glosa improvável (flag) fica em branco.",
       fmt_dinamico="FORMATO")

for rot, k in [("P25 do porte", "0.25"), ("Mediana do porte", "0.5"), ("P75 do porte", "0.75")]:
    ramos = "\n".join(
        f'            "{c}", PERCENTILEX.INC ( FILTER ( _grupo, NOT ISBLANK ( dOperadora[{c}] ){filtro_extra(c)} ), dOperadora[{c}], {k} ),'
        for c in CODIGOS)
    medida("dIndicador", "5. Ficha", rot,
           f"""
VAR _codigo = SELECTEDVALUE ( dIndicador[CODIGO] )
VAR _porte = SELECTEDVALUE ( dOperadora[PORTE] )
VAR _grupo =
    FILTER ( ALL ( dOperadora ), dOperadora[PORTE] = _porte && dOperadora[RANKING_OK] = TRUE () )
RETURN
    IF (
        NOT ISBLANK ( _porte ),
        SWITCH (
            _codigo,
{ramos.rstrip(',')}
        )
    )""", desc=f"{rot.split(' do ')[0]} das operadoras do ranking com o mesmo porte da escolhida. Reclamações só entre as com 20 mil clientes ou mais; glosa sem os valores improváveis.",
           fmt_dinamico="FORMATO")

medida("dIndicador", "5. Ficha", "Posição no porte",
       """
VAR _v = [Valor da operadora]
VAR _p25 = [P25 do porte]
VAR _p75 = [P75 do porte]
VAR _melhor = SELECTEDVALUE ( dIndicador[MELHOR] )
VAR _faixa =
    SWITCH (
        TRUE (),
        ISBLANK ( _v ) || ISBLANK ( _p25 ), BLANK (),
        _v < _p25, "entre as 25% mais baixas",
        _v > _p75, "entre as 25% mais altas",
        "na faixa do meio"
    )
VAR _juizo =
    SWITCH (
        TRUE (),
        _melhor = "menor" && _v < _p25, " (melhor)",
        _melhor = "menor" && _v > _p75, " (pior)",
        _melhor = "maior" && _v > _p75, " (melhor)",
        _melhor = "maior" && _v < _p25, " (pior)",
        ""
    )
RETURN
    IF ( NOT ISBLANK ( _faixa ) && SELECTEDVALUE ( dOperadora[RANKING_OK] ), _faixa & _juizo )""",
       desc="Onde a operadora fica entre as do mesmo porte. 'Melhor/pior' só aparece quando o indicador tem direção clara.")

medida("dOperadora", "5. Ficha", "Sinistralidade (12 meses) – mediana do porte",
       """
VAR _porte = SELECTEDVALUE ( dOperadora[PORTE] )
RETURN
    IF (
        NOT ISBLANK ( _porte ),
        CALCULATE (
            MEDIANX (
                FILTER ( VALUES ( dOperadora[REG] ), [Sinistralidade (12 meses)] >= 0.3 && [Sinistralidade (12 meses)] <= 1.5 ),
                [Sinistralidade (12 meses)]
            ),
            REMOVEFILTERS ( dOperadora ),
            dOperadora[PORTE] = _porte,
            dOperadora[RANKING_OK] = TRUE ()
        )
    )""", "0.0%", "Mediana, trimestre a trimestre, das operadoras do ranking com o mesmo porte da escolhida (porte atual).")

# --- Carteira
medida("fCarteira", "6. Carteira", "Clientes", "SUM ( fCarteira[ATIVOS] )", "#,0",
       "Vidas médico-hospitalares ativas (SIB/ANS) no mês do contexto.")
medida("fCarteira", "6. Carteira", "% com 59 anos ou mais",
       'DIVIDE ( CALCULATE ( [Clientes], fCarteira[FAIXA_REAJ] = "59 anos ou mais" ), [Clientes] )', "0.0%",
       "Última faixa de reajuste da ANS.")
medida("fCarteira", "6. Carteira", "% em plano individual",
       'DIVIDE ( CALCULATE ( [Clientes], fCarteira[CONTRATACAO] = "Individual ou familiar" ), [Clientes] )', "0.0%")

# --- Reclamações
medida("fIGR", "7. Reclamações", "Reclamações por 100 mil clientes",
       "DIVIDE ( SUM ( fIGR[QTD_RECLAMACOES] ), SUM ( fIGR[QTD_BENEFICIARIOS] ) ) * 100000", "#,0.0",
       "IGR da ANS: reclamações na NIP ÷ beneficiários da assistência médica × 100 mil, ponderado pelos meses do contexto.")

FORMATO_DIN = ('SWITCH ( SELECTEDVALUE ( dIndicador[FORMATO] ), "pct", "0.0%", "brl", "R$ #,0", '
               '"num0", "#,0", "num1", "#,0.0", "num3", "0.000", "#,0.0" )')


# ---------------------------------------------------------------- escrita
def escrever(caminho: pathlib.Path, texto: str):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8", newline="\n")


def bloco_dax(dax, nivel):
    ind = "\t" * nivel
    linhas = dax.split("\n")
    if len(linhas) == 1:
        return " " + linhas[0]
    return "\n" + "\n".join(ind + l if l.strip() else "" for l in linhas if l is not None)


def tabela_tmdl(nome):
    desc, ocultas, ordens = TABELAS[nome]
    sch = pq.read_schema(DADOS / f"{nome}.parquet")
    out = [f"/// {desc}", f"table {nome}", f"\tlineageTag: {tag(nome)}", ""]
    for m in [m for m in M if m["tabela"] == nome]:
        if m["desc"]:
            out.append(f"\t/// {m['desc']}")
        dax = m["dax"].lstrip("\n")
        out.append(f"\tmeasure {q(m['nome'])} ={bloco_dax(dax, 3)}")
        if m["fmt"]:
            out.append(f"\t\tformatString: {m['fmt']}")
        out.append(f"\t\tdisplayFolder: {m['pasta']}")
        out.append(f"\t\tlineageTag: {tag(nome, 'm', m['nome'])}")
        if m["fmt_din"]:  # objeto filho: vai por último, separado por linha em branco
            out.append("")
            out.append(f"\t\tformatStringDefinition = {FORMATO_DIN}")
        out.append("")
    for f in sch:
        tp = TIPO[str(f.type)]
        out += [f"\tcolumn {q(f.name)}", f"\t\tdataType: {tp}"]
        if tp == "dateTime":
            out.append("\t\tformatString: dd/mm/yyyy")
        if any(f.name.startswith(p) for p in ocultas):
            out.append("\t\tisHidden")
        out += ["\t\tsummarizeBy: none", f"\t\tsourceColumn: {f.name}", f"\t\tlineageTag: {tag(nome, 'c', f.name)}"]
        if f.name in ordens:
            out.append(f"\t\tsortByColumn: {ordens[f.name]}")
        out += ["", "\t\tannotation SummarizationSetBy = Automatic", ""]
    out += [f"\tpartition {nome} = m", "\t\tmode: import", "\t\tsource =",
            "\t\t\t\tlet",
            f'\t\t\t\t    Fonte = Parquet.Document ( File.Contents ( PastaDados & "{nome}.parquet" ) )',
            "\t\t\t\tin", "\t\t\t\t    Fonte", ""]
    return "\n".join(out)


def gerar_modelo():
    d = SM / "definition"
    if d.exists():
        shutil.rmtree(d)
    escrever(SM / "definition.pbism", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {}}, indent=2))
    escrever(d / "database.tmdl", "database\n\tcompatibilityLevel: 1606\n")
    refs = "\n".join(f"ref table {t}" for t in TABELAS)
    escrever(d / "model.tmdl", f"""model Model
\tculture: pt-BR
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tdiscourageImplicitMeasures
\tsourceQueryCulture: pt-BR
\tdataAccessOptions
\t\tlegacyRedirects
\t\treturnErrorValuesAsNull

annotation __PBI_TimeIntelligenceEnabled = 0

annotation PBI_QueryOrder = {json.dumps(["PastaDados"] + list(TABELAS))}

{refs}
""")
    pasta = str(DADOS) + "\\"
    escrever(d / "expressions.tmdl", f"""/// Pasta com os parquet gerados por scripts/exportar_pbi.py. Quem clonar o repositório troca aqui e atualiza.
expression PastaDados = "{pasta}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
\tlineageTag: {tag('PastaDados')}

\tannotation PBI_ResultType = Text
""")
    rel = []
    for a, ca, b, cb in RELACOES:
        rel += [f"relationship {tag('rel', a, ca, b, cb)}", f"\tfromColumn: {a}.{ca}", f"\ttoColumn: {b}.{cb}", ""]
    escrever(d / "relationships.tmdl", "\n".join(rel))
    for t in TABELAS:
        escrever(d / "tables" / f"{t}.tmdl", tabela_tmdl(t))


def gerar_relatorio_base():
    """Cria o esqueleto do relatório só se ainda não existir (as páginas são geradas à parte)."""
    if (RP / "definition" / "report.json").exists():
        return
    escrever(PASTA / f"{NOME}.pbip", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{NOME}.Report"}}],
        "settings": {"enableAutoRecovery": True}}, indent=2))
    escrever(RP / "definition.pbir", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NOME}.SemanticModel"}}}, indent=2))
    escrever(RP / "definition" / "version.json", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0"}, indent=2))
    tema = "Fluent2-CY26SU05"
    destino = RP / "StaticResources" / "SharedResources" / "BaseThemes" / f"{tema}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(PASTA / "_modelo" / f"{tema}.json", destino)
    escrever(RP / "definition" / "report.json", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
        "themeCollection": {"baseTheme": {"name": tema, "reportVersionAtImport": {"visual": "2.9.0", "report": "3.3.0", "page": "2.3.1"},
                                          "type": "SharedResources"}},
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources",
                              "items": [{"name": tema, "path": f"BaseThemes/{tema}.json", "type": "BaseTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized",
                     "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                     "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}}, indent=2))
    pid = "p01gancho"
    escrever(RP / "definition" / "pages" / "pages.json", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
        "pageOrder": [pid], "activePageName": pid}, indent=2))
    escrever(RP / "definition" / "pages" / pid / "page.json", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
        "name": pid, "displayName": "O lucro vem das aplicações", "displayOption": "FitToPage",
        "height": 720, "width": 1280}, indent=2))


if __name__ == "__main__":
    gerar_modelo()
    gerar_relatorio_base()
    print(f"modelo: {len(TABELAS)} tabelas, {len(RELACOES)} relações, {len(M)} medidas -> {SM}")
