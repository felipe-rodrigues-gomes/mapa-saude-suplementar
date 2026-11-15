"""Gera as páginas do relatório (PBIR) e o tema do projeto.

Páginas: 1) O lucro vem das aplicações  2) Ficha da operadora
Rodar com o Power BI Desktop FECHADO (ele sobrescreve arquivos alterados por fora).
Uso: python -I scripts/gerar_paginas.py
"""
import json, hashlib, shutil, stat, os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import RAIZ

RP = RAIZ / "powerbi" / "MapaSaudeSuplementar.Report"
DEF = RP / "definition"
SCH_VIS = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.7.0/schema.json"
SCH_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"

# identidade (a mesma da página HTML)
COR = dict(papel="#F6F4EF", tinta="#12324A", cinza="#5B6770", claro="#8AA1B1", linha="#E3E0D8",
           operacao="#D1495B", aplicacoes="#2A9D8F", destaque="#E9A23B", branco="#FFFFFF")
FONTE = "Segoe UI"
FONTE_FORTE = "Segoe UI Semibold"
W, H = 1280, 720


# ------------------------------------------------------------------ utilitários PBIR
def nid(*partes):
    return hashlib.md5("/".join(partes).encode()).hexdigest()[:20]


def L(v):
    """Literal PBIR: bool, número (D), texto (entre aspas simples)."""
    if isinstance(v, bool):
        s = "true" if v else "false"
    elif isinstance(v, (int, float)):
        s = f"{v}D"
    else:
        s = "'" + str(v).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": s}}}


def cor(c):
    return {"solid": {"color": L(c)}}


def props(**kw):
    return {"properties": {k: (v if isinstance(v, dict) else L(v)) for k, v in kw.items()}}


def campo(tabela, prop, medida=True):
    tipo = "Measure" if medida else "Column"
    return {tipo: {"Expression": {"SourceRef": {"Entity": tabela}}, "Property": prop}}


def proj(tabela, prop, medida=True, nome=None, ativo=None):
    p = {"field": campo(tabela, prop, medida), "queryRef": f"{tabela}.{prop}", "nativeQueryRef": nome or prop}
    if nome:
        p["displayName"] = nome
    if ativo is not None:
        p["active"] = ativo
    return p


def container(titulo=None, ajuda=None, fundo=True, borda=False):
    o = {"title": [props(show=bool(titulo))] if not titulo else
         [props(show=True, text=titulo, fontSize=11, fontFamily=FONTE_FORTE, fontColor=cor(COR["tinta"]))],
         "subTitle": [props(show=False)],
         "background": [props(show=fundo, color=cor(COR["branco"]), transparency=0)],
         "border": [props(show=borda, color=cor(COR["linha"]), radius=6)],
         "dropShadow": [props(show=False)],
         "padding": [props(top=8, bottom=8, left=10, right=10)]}
    if ajuda:
        o["visualHeader"] = [props(show=True, showTooltipButton=True, showFocusModeButton=False, showOptionsMenu=True)]
        o["visualHeaderTooltip"] = [props(type="Default", text=ajuda, titleFontColor=cor(COR["tinta"]))]
    else:
        o["visualHeader"] = [props(show=False)]
    return o


def visual(pagina, nome, x, y, w, h, z, corpo):
    return {"$schema": SCH_VIS, "name": nid(pagina, nome),
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z}, "visual": corpo}


def texto(pagina, nome, x, y, w, h, z, linhas):
    """linhas = [(texto, tamanho_pt, cor, negrito)]"""
    pars = [{"textRuns": [{"value": t, "textStyle": {"fontFamily": FONTE_FORTE if b else FONTE,
                                                     "fontSize": f"{s}pt", "color": c}}]} for t, s, c, b in linhas]
    corpo = {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": pars}}]},
             "visualContainerObjects": {"title": [props(show=False)], "background": [props(show=False)],
                                        "border": [props(show=False)], "visualHeader": [props(show=False)]},
             "drillFilterOtherVisuals": True}
    return visual(pagina, nome, x, y, w, h, z, corpo)


def cartao(pagina, nome, x, y, w, h, z, tabela, medida, rotulo, cor_valor, tam=26, ajuda=None, fmt_unidade=1):
    corpo = {"visualType": "cardVisual",
             "query": {"queryState": {"Data": {"projections": [proj(tabela, medida)]}}},
             "objects": {
                 "value": [{**props(fontSize=tam, fontColor=cor(cor_valor), bold=True, fontFamily=FONTE_FORTE,
                                    horizontalAlignment="left", labelDisplayUnits=fmt_unidade), "selector": {"id": "default"}}],
                 "label": [{**props(show=True, text=rotulo, fontSize=10, fontColor=cor(COR["cinza"]),
                                    position="belowValue", horizontalAlignment="left", fontFamily=FONTE),
                            "selector": {"id": "default"}}],
                 "layout": [props(alignment="left")],
                 "outline": [props(show=False), {**props(show=False), "selector": {"id": "default"}}],
                 "accentBar": [props(show=False), {**props(show=False), "selector": {"id": "default"}}],
                 "fillCustom": [props(show=False), {**props(show=False), "selector": {"id": "default"}}],
             },
             "visualContainerObjects": container(ajuda=ajuda),
             "drillFilterOtherVisuals": True}
    return visual(pagina, nome, x, y, w, h, z, corpo)


def cartao_texto(pagina, nome, x, y, w, h, z, tabela, medida, tam, cor_valor, negrito=False, ajuda=None):
    v = cartao(pagina, nome, x, y, w, h, z, tabela, medida, "", cor_valor, tam, ajuda)
    o = v["visual"]["objects"]
    o["label"] = [{**props(show=False), "selector": {"id": "default"}}]
    o["value"][0]["properties"]["bold"] = L(negrito)
    o["value"][0]["properties"]["fontFamily"] = L(FONTE_FORTE if negrito else FONTE)
    o["padding"] = [{**props(paddingUniform=0), "selector": {"id": "default"}}]
    v["visual"]["visualContainerObjects"]["background"] = [props(show=False)]
    v["visual"]["visualContainerObjects"]["padding"] = [props(top=0, bottom=0, left=0, right=0)]
    return v


def segmentacao(pagina, nome, x, y, w, h, z, tabela, coluna, cabecalho, unico=False, busca=False):
    obj = {"data": [props(mode="Dropdown")],
           "header": [props(show=True, text=cabecalho, textSize=9, fontColor=cor(COR["cinza"]), fontFamily=FONTE)],
           "items": [props(textSize=11, fontColor=cor(COR["tinta"]), fontFamily=FONTE)],
           "selection": [props(singleSelect=unico, strictSingleSelect=unico, selectAllCheckboxEnabled=not unico)]}
    if busca:
        obj["general"] = [props(selfFilterEnabled=True)]
    corpo = {"visualType": "slicer",
             "query": {"queryState": {"Values": {"projections": [proj(tabela, coluna, False, ativo=True)]}}},
             "objects": obj, "visualContainerObjects": container(fundo=False),
             "drillFilterOtherVisuals": True}
    return visual(pagina, nome, x, y, w, h, z, corpo)


def filtro_coluna(tabela, coluna, valores, nome):
    """Filtro de visual/página por lista de valores (sem invólucro 'expr', senão o Desktop não renderiza)."""
    return {"name": nome, "field": campo(tabela, coluna, False), "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": tabela, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [campo("t", coluna, False) | {}],
                                                       "Values": [[{"Literal": {"Value": v}}] for v in valores]}}}]}}


def _fix_source(f):
    # dentro do filtro a coluna referencia o alias 't' por Source, não por Entity
    c = f["filter"]["Where"][0]["Condition"]["In"]["Expressions"][0]
    col = c["Column"]
    col["Expression"] = {"SourceRef": {"Source": "t"}}
    return f


# ------------------------------------------------------------------ página 1: o gancho
def pagina_gancho():
    p = "p01gancho"
    vs = []
    vs.append(texto(p, "titulo", 32, 10, 950, 78, 1000, [
        ("Em cinco anos, os planos de saúde perderam dinheiro na operação.", 20, COR["tinta"], True),
        ("O lucro veio das aplicações financeiras.", 20, COR["aplicacoes"], True)]))
    vs.append(texto(p, "subtitulo", 32, 88, 1216, 24, 1001, [
        ("Operadoras médico-hospitalares, 2021 a 2025. Operação = mensalidades menos atendimento, administração e venda. "
         "Aplicações = rendimento do dinheiro guardado.", 10, COR["cinza"], False)]))
    vs.append(segmentacao(p, "seg_modalidade", 1008, 16, 240, 56, 1002, "dOperadora", "MODALIDADE", "Modalidade"))
    # números do período
    vs.append(cartao(p, "c_operacao", 32, 118, 290, 100, 10, "fContabil", "Resultado da operação 2021–2025 (R$ bi)",
                     "R$ bi: operação do plano, 2021–25", COR["operacao"], 30,
                     "Soma, de 2021 a 2025, das receitas da operação de saúde menos atendimento, administração, comercialização e outras despesas operacionais (DIOPS/ANS, contas 31+32+33+34+37 − 41−43−44−46)."))
    vs.append(cartao(p, "c_aplicacoes", 338, 118, 290, 100, 11, "fContabil", "Resultado das aplicações 2021–2025 (R$ bi)",
                     "R$ bi: aplicações financeiras, 2021–25", COR["aplicacoes"], 30,
                     "Receitas financeiras menos despesas financeiras (contas 35 − 45), soma de 2021 a 2025."))
    vs.append(cartao(p, "c_lucro", 644, 118, 290, 100, 12, "fContabil", "Lucro líquido 2021–2025 (R$ bi)",
                     "R$ bi: lucro líquido, 2021–25", COR["tinta"], 30,
                     "Receitas − despesas − impostos e participações (contas 3 − 4 − 61), soma de 2021 a 2025. Bate com os números divulgados pela ANS."))
    vs.append(cartao(p, "c_salvas", 950, 118, 298, 100, 13, "dOperadora", "% salvas pelas aplicações",
                     "só lucram graças às aplicações", COR["destaque"], 30,
                     "Operadoras do ranking com resultado da operação negativo e lucro líquido positivo nos 12 meses até jun/2026."))
    # gráfico combinado: operação e aplicações em colunas, lucro em linha
    combo = {"visualType": "lineClusteredColumnComboChart",
             "query": {"queryState": {
                 "Category": {"projections": [proj("dTrimestre", "ANO", False, "Ano", True)]},
                 "Y": {"projections": [proj("fContabil", "Resultado da operação (R$ bi)", nome="Operação do plano"),
                                       proj("fContabil", "Resultado das aplicações (R$ bi)", nome="Aplicações financeiras")]},
                 "Y2": {"projections": [proj("fContabil", "Lucro líquido (R$ bi)", nome="Lucro líquido")]}},
                 "sortDefinition": {"sort": [{"field": campo("dTrimestre", "ANO", False), "direction": "Ascending"}]}},
             "objects": {
                 "dataPoint": [
                     {**props(fill=cor(COR["operacao"])), "selector": {"metadata": "fContabil.Resultado da operação (R$ bi)"}},
                     {**props(fill=cor(COR["aplicacoes"])), "selector": {"metadata": "fContabil.Resultado das aplicações (R$ bi)"}},
                     {**props(fill=cor(COR["tinta"])), "selector": {"metadata": "fContabil.Lucro líquido (R$ bi)"}}],
                 "legend": [props(show=True, position="Top", fontSize=10, showTitle=False, labelColor=cor(COR["cinza"]))],
                 "categoryAxis": [props(fontSize=10, showAxisTitle=False, axisType="Categorical", labelColor=cor(COR["cinza"]))],
                 "valueAxis": [props(show=True, fontSize=9, showAxisTitle=False, secShow=False, gridlineShow=True,
                                     labelColor=cor(COR["claro"]))],
                 "labels": [props(show=True, fontSize=9, labelDisplayUnits=1, labelPrecision=1, color=cor(COR["tinta"]))],
                 "lineStyles": [props(strokeWidth=3, showMarker=True, markerSize=6)],
             },
             "visualContainerObjects": container(
                 "Ano a ano: a operação só voltou ao azul em 2024; as aplicações renderam em todos os anos (R$ bilhões)",
                 "Ano fechado (acumulado do 4º trimestre). Colunas: resultado da operação e das aplicações. Linha: lucro líquido. Fonte: demonstrações contábeis (DIOPS) da ANS."),
             "drillFilterOtherVisuals": True}
    v = visual(p, "combo", 32, 232, 900, 440, 20, combo)
    v["filterConfig"] = {"filters": [_fix_source(filtro_coluna("dTrimestre", "ANO", ["2021L", "2022L", "2023L", "2024L", "2025L"], "f_anos"))]}
    vs.append(v)
    # leitura justa, ao lado
    vs.append(texto(p, "leitura", 950, 232, 298, 440, 21, [
        ("Como ler", 12, COR["tinta"], True),
        ("Aplicar as reservas faz parte do negócio: a ANS exige que as operadoras guardem dinheiro para pagar os atendimentos já feitos.", 10, COR["cinza"], False),
        ("", 6, COR["cinza"], False),
        ("O que surpreende é a proporção. Entre 2021 e 2023 a operação teve prejuízo em todos os anos, e foi o financeiro que segurou o resultado.", 10, COR["cinza"], False),
        ("", 6, COR["cinza"], False),
        ("Mesmo em 2025, o melhor ano da série, as aplicações renderam 1,5 vez o que a operação rendeu.", 10, COR["cinza"], False),
        ("", 6, COR["cinza"], False),
        ("Conferido com os números divulgados pela ANS para 2022, 2023 e 2025.", 9, COR["claro"], False)]))
    vs.append(texto(p, "fonte", 32, 680, 1216, 24, 30, [
        ("Fonte: ANS, demonstrações contábeis (DIOPS) e cadastro de operadoras. Operadoras com beneficiários de assistência médica. Elaboração própria.", 8, COR["claro"], False)]))
    return p, "O lucro vem das aplicações", vs, None


# ------------------------------------------------------------------ página 2: ficha
def pagina_ficha():
    p = "p02ficha"
    vs = []
    sb = segmentacao(p, "busca", 32, 18, 420, 56, 1000, "dOperadora", "BUSCA", "Procure a sua operadora (nome ou registro ANS)", unico=True, busca=True)
    sb["visual"]["objects"]["general"][0]["properties"].update({"filter": {"filter": {
        "Version": 2, "From": [{"Name": "d", "Entity": "dOperadora", "Type": 0}],
        "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": "BUSCA"}}],
                                        "Values": [[{"Literal": {"Value": "'AMIL · 326305'"}}]]}}}]}}})
    sb["filterConfig"] = {"filters": [_fix_source(filtro_coluna("dOperadora", "ATIVA", ["true"], "f_ativas"))]}
    vs.append(sb)
    vs.append(cartao_texto(p, "nome", 476, 16, 772, 34, 1001, "dOperadora", "Operadora escolhida", 18, COR["tinta"], True))
    vs.append(cartao_texto(p, "perfil", 476, 50, 772, 20, 1002, "dOperadora", "Perfil da operadora", 10, COR["cinza"]))
    vs.append(cartao_texto(p, "aviso", 476, 70, 772, 20, 1003, "dOperadora", "Aviso de ranking", 10, COR["destaque"], True))
    # tabela: indicador × operadora × porte
    cols = [("dIndicador", "INDICADOR", False, "Indicador"), ("dIndicador", "Valor da operadora", True, "Operadora"),
            ("dIndicador", "P25 do porte", True, "25% do porte"), ("dIndicador", "Mediana do porte", True, "Mediana do porte"),
            ("dIndicador", "P75 do porte", True, "75% do porte"), ("dIndicador", "Posição no porte", True, "Onde fica")]
    cols = [c for c in cols if c[1] not in ("P25 do porte", "P75 do porte")]
    larg = {"INDICADOR": 300, "Valor da operadora": 84, "Mediana do porte": 112, "Posição no porte": 250}
    tab = {"visualType": "tableEx",
           "query": {"queryState": {"Values": {"projections": [proj(t, c, m, n) for t, c, m, n in cols]}},
                     "sortDefinition": {"sort": [{"field": campo("dIndicador", "INDICADOR", False), "direction": "Ascending"}]}},
           "objects": {
               "columnHeaders": [props(fontSize=9, bold=True, fontColor=cor(COR["tinta"]), wordWrap=False,
                                       autoSizeColumnWidth=False, alignment="Center", backColor=cor(COR["papel"]))],
               "values": [props(fontSize=10, fontColor=cor(COR["tinta"]), wordWrap=False, backColorPrimary=cor(COR["branco"]),
                                backColorSecondary=cor(COR["branco"]))],
               "total": [props(totals=False)],
               "grid": [props(rowPadding=3, gridVertical=False, gridHorizontal=True, gridHorizontalColor=cor(COR["linha"]),
                              outlineColor=cor(COR["linha"]))],
               "columnWidth": [{**props(value=v), "selector": {"metadata": f"dIndicador.{k}"}} for k, v in larg.items()],
               "columnFormatting": [{**props(alignment="Center"), "selector": {"metadata": f"dIndicador.{k}"}}
                                    for k in ["Valor da operadora", "Mediana do porte"]] +
                                   [{**props(alignment="Left", styleValues=True, styleHeader=False, styleTotal=False),
                                     "selector": {"metadata": f"dIndicador.{k}"}} for k in ["INDICADOR", "Posição no porte"]]},
           "visualContainerObjects": container(
               "Como a operadora se compara com as do mesmo porte",
               "Valor da operadora e distribuição entre as operadoras do ranking com o mesmo porte (pequeno: até 20 mil vidas; médio: até 100 mil; grande: mais de 100 mil). "
               "25%/75%: um quarto das operadoras fica abaixo/acima. 'Melhor/pior' só aparece quando o indicador tem direção clara. A página «Como foi feito» do site traz a fórmula de cada indicador."),
           "drillFilterOtherVisuals": True}
    vs.append(visual(p, "tabela", 32, 98, 816, 486, 10, tab))
    # tendência da sinistralidade × mediana do porte
    linha = {"visualType": "lineChart",
             "query": {"queryState": {
                 "Category": {"projections": [proj("dTrimestre", "ROTULO_CURTO", False, "Trimestre", True)]},
                 "Y": {"projections": [proj("fContabil", "Sinistralidade (12 meses)", nome="Operadora"),
                                       proj("dOperadora", "Sinistralidade (12 meses) – mediana do porte", nome="Mediana do porte")]}},
                 "sortDefinition": {"sort": [{"field": campo("dTrimestre", "ROTULO_CURTO", False), "direction": "Ascending"}]}},
             "objects": {
                 "dataPoint": [{**props(fill=cor(COR["tinta"])), "selector": {"metadata": "fContabil.Sinistralidade (12 meses)"}},
                               {**props(fill=cor(COR["claro"])), "selector": {"metadata": "dOperadora.Sinistralidade (12 meses) – mediana do porte"}}],
                 "lineStyles": [props(strokeWidth=3), {**props(lineStyle="dashed", strokeWidth=2),
                                                       "selector": {"metadata": "dOperadora.Sinistralidade (12 meses) – mediana do porte"}}],
                 "legend": [props(show=True, position="Top", fontSize=9, showTitle=False)],
                 "categoryAxis": [props(fontSize=8, showAxisTitle=False, labelColor=cor(COR["cinza"]), preferredCategoryWidth=20)],
                 "valueAxis": [props(fontSize=8, showAxisTitle=False, labelColor=cor(COR["claro"]))]},
             "visualContainerObjects": container("Quanto da mensalidade volta em atendimento, 12 meses",
                                                 "Sinistralidade em 12 meses móveis (critério da ANS), trimestre a trimestre, comparada com a mediana das operadoras do mesmo porte."),
             "drillFilterOtherVisuals": True}
    v = visual(p, "linha_sinist", 862, 98, 386, 236, 11, linha)
    v["filterConfig"] = {"filters": [_fix_source(filtro_coluna("dTrimestre", "ANO", ["2023L", "2024L", "2025L", "2026L"], "f_anos"))]}
    vs.append(v)
    # forma de pagamento à rede (12 meses até o último trimestre)
    barras = {"visualType": "clusteredBarChart",
              "query": {"queryState": {
                  "Category": {"projections": [proj("dFormaPagamento", "FORMA", False, "Forma", True)]},
                  "Y": {"projections": [proj("dFormaPagamento", "% dos eventos (forma de pagamento)", nome="% dos eventos")]}},
                  "sortDefinition": {"sort": [{"field": campo("dFormaPagamento", "FORMA", False), "direction": "Ascending"}]}},
              "objects": {"dataPoint": [props(fill=cor(COR["aplicacoes"]))],
                          "labels": [props(show=True, fontSize=9, labelPrecision=0, color=cor(COR["tinta"]))],
                          "legend": [props(show=False)],
                          "categoryAxis": [props(fontSize=9, showAxisTitle=False, labelColor=cor(COR["cinza"]))],
                          "valueAxis": [props(show=False)]},
              "visualContainerObjects": container("Como paga a rede (12 meses até jun/2026)",
                                                  "Parte dos eventos conhecidos ou avisados paga em cada forma ao prestador (contas 4111 a 4119 do DIOPS), 12 meses."),
              "drillFilterOtherVisuals": True}
    v = visual(p, "barras_rede", 862, 346, 386, 238, 12, barras)
    v["filterConfig"] = {"filters": [_fix_source(filtro_coluna("dTrimestre", "PERIODO", ["'2026T2'"], "f_periodo"))]}
    vs.append(v)
    vs.append(texto(p, "rodape", 32, 596, 1216, 110, 30, [
        ("Como ler", 11, COR["tinta"], True),
        ("Contabilidade, carteira e reclamações: 12 meses até jun/2026. Nota de qualidade (IDSS): 2025, ano-base 2024. Glosa: 2º semestre de 2025. "
         "SUS: atendimentos de 2024 identificados no ressarcimento. Uma operadora entra no ranking com 1.000 vidas médicas ou mais, balanço dos últimos 12 meses e sinistralidade entre 30% e 150%; "
         "as demais aparecem sem comparação, com o motivo.", 9, COR["cinza"], False),
        ("Fonte: ANS (DIOPS, SIB, IGR, IDSS, painel de glosas, ressarcimento ao SUS). Elaboração própria.", 8, COR["claro"], False)]))
    return p, "Ficha da operadora", vs, None


# ------------------------------------------------------------------ gravação
def _sem_somente_leitura(func, caminho, _exc):
    os.chmod(caminho, stat.S_IWRITE)
    func(caminho)


def gravar(paginas):
    pdir = DEF / "pages"
    if pdir.exists():
        shutil.rmtree(pdir, onexc=_sem_somente_leitura)
    ordem = []
    for pid, nome, vs, extra in paginas:
        ordem.append(pid)
        pj = {"$schema": SCH_PAGE, "name": pid, "displayName": nome, "displayOption": "FitToPage",
              "height": H, "width": W,
              "objects": {"background": [props(color=cor(COR["papel"]), transparency=0)],
                          "outspace": [props(color=cor(COR["papel"]), transparency=0)]}}
        (pdir / pid).mkdir(parents=True, exist_ok=True)
        (pdir / pid / "page.json").write_text(json.dumps(pj, ensure_ascii=False, indent=2), encoding="utf-8")
        for v in vs:
            d = pdir / pid / "visuals" / v["name"]
            d.mkdir(parents=True, exist_ok=True)
            (d / "visual.json").write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")
    (pdir / "pages.json").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
        "pageOrder": ordem, "activePageName": ordem[0]}, indent=2), encoding="utf-8")
    print(f"{len(paginas)} páginas, {sum(len(v) for _, _, v, _ in paginas)} visuais")


if __name__ == "__main__":
    gravar([pagina_gancho(), pagina_ficha()])
