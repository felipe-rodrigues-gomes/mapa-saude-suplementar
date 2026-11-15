"""Ressarcimento ao SUS -> dois fatos agregados.

fato_ressarc_uso.parquet       (arquivo "beneficiários identificados / ABI")
  ano-mês do atendimento × operadora × UF do beneficiário × UF do estabelecimento × tipo (AIH/APAC) × especialidade
  -> atendimentos, valor do atendimento (tabela SUS), valor cobrado (com IVR), valor pago
fato_ressarc_cobranca.parquet  (arquivo "por operadora")
  ano-mês do atendimento × operadora × status da análise × situação da GRU × dívida ativa
  -> atendimentos, valor do atendimento, valor cobrado

Atenção: o ressarcimento anda devagar (identificação, impugnação, recurso, cobrança).
Atendimentos dos últimos ~2 anos ainda estão sendo processados: valores recentes são parciais.
Uso: python -I scripts/etl_ressarcimento.py
"""
import io, sys, pathlib, zipfile, re
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *

ANOS = range(2019, 2026)
Z = BRUTOS / "ressarcimento"


def ler_membro(zf, nome, usecols, chunks=1_000_000):
    with zf.open(nome) as f:
        amostra = f.read(3_000_000)
    enc = "utf-8"
    try:
        amostra[:-8].decode("utf-8")   # corta o fim para não quebrar caractere no meio
    except UnicodeDecodeError:
        enc = "latin-1"
    with zf.open(nome) as f:
        yield from pd.read_csv(io.TextIOWrapper(f, encoding=enc, errors="replace"), sep=";", dtype=str,
                               usecols=usecols, chunksize=chunks)


def classificar(ch: pd.DataFrame) -> pd.DataFrame:
    """Motivo provável do uso do SUS e o grupo de leitura (validado com o Felipe em 15/11/2026).

    O dado não traz se o atendimento foi de urgência nem se o plano cobre obstetrícia: a regra usa o
    procedimento principal (SIGTAP), o CID e a segmentação do plano, e na dúvida fica na zona cinzenta.
    Ordem: a primeira regra que bate vale.
    """
    proc = ch.COD_PROCEDIMENTO.fillna("").str.replace(r"\D", "", regex=True).str.zfill(10)
    sub, grp = proc.str[:4], proc.str[:2]
    cid = ch.COD_CID.fillna("").str.upper().str.strip()
    esp = ch.ESPECIALIDADE.fillna("").str.upper()
    seg = ch.SEGMENTACAO_PLANO.fillna("").str.upper()
    aih = ch.TIPO.str.startswith("Internação")
    regras = [
        # 1. Não indica falha da operadora
        ("Não indica falha", "Transplante", grp == "05"),
        ("Não indica falha", "Trauma / causa externa", (sub == "0308") | cid.str.match(r"^[STVWXY]")),
        ("Não indica falha", "Fora da cobertura do plano", (aih & seg.str.startswith("AMBULATORIAL"))
                                                           | (~aih & (seg == "HOSPITALAR"))),
        # 3. Provável falha de acesso (procedimento coberto e, em regra, programável)
        ("Provável falha de acesso", "Parto e obstetrícia", sub.isin(["0310", "0411"]) | cid.str.startswith("O")),
        ("Provável falha de acesso", "Psiquiatria", esp.str.contains("PSIQUIATRIA") | cid.str.startswith("F")),
        ("Zona cinzenta", "Diálise e nefrologia", sub.isin(["0305", "0418"])),   # 0418 = fístula para diálise
        ("Provável falha de acesso", "Cirurgia eletiva", sub.isin(["0401", "0404", "0407", "0408", "0409", "0410",
                                                                   "0412", "0413", "0414", "0415"])),
        # 2. Zona cinzenta (continuidade de tratamento, centro de referência, rede escassa)
        ("Zona cinzenta", "Oncologia", sub.isin(["0304", "0416"]) | cid.str.match(r"^C|^D0|^D[1-4]")),
        ("Zona cinzenta", "Olhos (catarata e outras)", sub == "0405"),
        ("Zona cinzenta", "Cardiovascular", sub == "0406"),
        ("Zona cinzenta", "Medicamento de alto custo", grp == "06"),
        ("Zona cinzenta", "Diagnóstico de alta complexidade", grp == "02"),
        ("Zona cinzenta", "Internação clínica", aih & (grp == "03")),
    ]
    ch["GRUPO_LEITURA"] = "Zona cinzenta"
    ch["MOTIVO"] = "Outros"
    ja = pd.Series(False, index=ch.index)
    for g, m, cond in regras:
        bate = cond & ~ja
        ch.loc[bate, "GRUPO_LEITURA"] = g
        ch.loc[bate, "MOTIVO"] = m
        ja |= bate
    return ch


def uso():
    zf = zipfile.ZipFile(Z / "abi.zip")
    cols = ["COMPETENCIA", "REGISTRO_OPERADORA", "TIPO_ATENDIMENTO", "UF_BENEFICIARIO", "UF_ESTAB",
            "ESPECIALIDADE", "COD_PROCEDIMENTO", "COD_CID", "SEGMENTACAO_PLANO",
            "VL_ATENDIMENTO", "VL_RESSARC", "VL_PAGO_RESSARC"]
    chave = ["COMPETENCIA", "REG", "TIPO", "UF_BENEFICIARIO", "UF_ESTAB", "ESPECIALIDADE", "GRUPO_LEITURA", "MOTIVO"]
    partes = []
    for nome in sorted(zf.namelist()):
        if int(re.search(r"(\d{4})", nome).group(1)) < min(ANOS) - 1:
            continue
        for ch in ler_membro(zf, nome, cols):
            mm, aa = ch.COMPETENCIA.str.split("/", expand=True)[0], ch.COMPETENCIA.str.split("/", expand=True)[1]
            ch["COMPETENCIA"] = aa + mm
            ch = ch[ch.COMPETENCIA.str[:4].astype(int).isin(ANOS)]
            if ch.empty: continue
            ch["REG"] = reg(ch.REGISTRO_OPERADORA)
            ch["TIPO"] = ch.TIPO_ATENDIMENTO.map({"01": "Internação (AIH)", "1": "Internação (AIH)",
                                                  "02": "Alta complexidade ambulatorial (APAC)", "2": "Alta complexidade ambulatorial (APAC)"}).fillna("Outro")
            ch = classificar(ch)
            ch["ESPECIALIDADE"] = ch.ESPECIALIDADE.fillna("Não se aplica (APAC)")
            for c in ["VL_ATENDIMENTO", "VL_RESSARC", "VL_PAGO_RESSARC"]:
                ch[c] = num_br(ch[c]).fillna(0)
            ch["ATENDIMENTOS"] = 1
            partes.append(ch.groupby(chave, dropna=False)[["ATENDIMENTOS", "VL_ATENDIMENTO", "VL_RESSARC", "VL_PAGO_RESSARC"]].sum().reset_index())
        print(f"  ABI {nome} ok", flush=True)
    d = pd.concat(partes).groupby(chave, dropna=False).sum().reset_index()
    d.to_parquet(TRATADOS / "fato_ressarc_uso.parquet", index=False)
    print(f"fato_ressarc_uso: {len(d):,} linhas | atendimentos por ano:",
          d.groupby(d.COMPETENCIA.str[:4]).ATENDIMENTOS.sum().to_dict())
    t = d.groupby(["GRUPO_LEITURA", "MOTIVO"])[["ATENDIMENTOS", "VL_ATENDIMENTO"]].sum()
    t = (t / t.sum() * 100).round(1)
    print(t.to_string())


def rotular(d: pd.DataFrame) -> pd.DataFrame:
    """Rótulos legíveis para status e situação da cobrança (a origem vem com acentos corrompidos)."""
    s = d.STATUS_ANALISE
    d["INSTANCIA"] = s.str.extract(r"EM ([12])")[0].map({"1": "1ª instância", "2": "2ª instância"}).fillna("—")
    d["RESULTADO_ANALISE"] = "Outro"
    d.loc[s.str.startswith("N") & s.str.contains("IMPUGNADA") & ~s.str.contains("INTEMP"), "RESULTADO_ANALISE"] = "Não contestado pela operadora"
    d.loc[s.str.startswith("AVALIANDO"), "RESULTADO_ANALISE"] = "Em análise"
    d.loc[s.str.startswith("DEFERIDA"), "RESULTADO_ANALISE"] = "Contestação aceita (não cobra)"
    d.loc[s.str.startswith("INDEFERIDA"), "RESULTADO_ANALISE"] = "Contestação negada (cobra)"
    d.loc[s.str.contains("INTEMPESTIV"), "RESULTADO_ANALISE"] = "Contestação fora do prazo (cobra)"
    g = d.SITUACAO_GRU.str.lower()
    d["SITUACAO_COBRANCA"] = "Sem cobrança emitida"
    d.loc[g.str.startswith("pago"), "SITUACAO_COBRANCA"] = "Pago"
    d.loc[g.str.startswith("parcelado"), "SITUACAO_COBRANCA"] = "Parcelado"
    d.loc[g.str.startswith("pendente"), "SITUACAO_COBRANCA"] = "Pendente"
    d.loc[g.str.startswith("suspenso"), "SITUACAO_COBRANCA"] = "Suspenso na Justiça"
    return d


def cobranca():
    zf = zipfile.ZipFile(Z / "operadora.zip")
    cols = ["COMPETENCIA", "REGISTRO_OPERADORA", "STATUS_ANALISE_ATENDIMENTO", "SITUACAO_GRU",
            "DATA_DIVIDA_ATIVA", "VALOR_ATENDIMENTO", "VALOR_COBRADO"]
    chave = ["COMPETENCIA", "REG", "STATUS_ANALISE", "SITUACAO_GRU", "DIVIDA_ATIVA"]
    partes = []
    for nome in sorted(zf.namelist()):
        if int(re.search(r"(\d{4})", nome).group(1)) < min(ANOS):
            continue
        for ch in ler_membro(zf, nome, cols):
            ch["COMPETENCIA"] = ch.COMPETENCIA.str.replace("-", "")
            ch = ch[ch.COMPETENCIA.str[:4].astype(int).isin(ANOS)]
            if ch.empty: continue
            ch["REG"] = reg(ch.REGISTRO_OPERADORA)
            # status com acento corrompido em parte dos arquivos: guarda a versão sem acento
            ch["STATUS_ANALISE"] = (ch.STATUS_ANALISE_ATENDIMENTO.fillna("SEM STATUS").str.upper()
                                    .str.replace(r"[^A-Z0-9 ]", "", regex=True).str.replace(r"\s+", " ", regex=True))
            ch["SITUACAO_GRU"] = ch.SITUACAO_GRU.fillna("Sem GRU")
            ch["DIVIDA_ATIVA"] = ch.DATA_DIVIDA_ATIVA.notna()
            for c in ["VALOR_ATENDIMENTO", "VALOR_COBRADO"]:
                ch[c] = num_br(ch[c]).fillna(0)
            ch["ATENDIMENTOS"] = 1
            partes.append(ch.groupby(chave, dropna=False)[["ATENDIMENTOS", "VALOR_ATENDIMENTO", "VALOR_COBRADO"]].sum().reset_index())
        print(f"  operadora {nome} ok", flush=True)
    d = rotular(pd.concat(partes).groupby(chave, dropna=False).sum().reset_index())
    d.to_parquet(TRATADOS / "fato_ressarc_cobranca.parquet", index=False)
    resumo(d)


def resumo(d):
    print(f"fato_ressarc_cobranca: {len(d):,} linhas")
    print("análise (atendimentos):", d.groupby("RESULTADO_ANALISE").ATENDIMENTOS.sum().to_dict())
    print("cobrança (R$ mi cobrados):", (d.groupby("SITUACAO_COBRANCA").VALOR_COBRADO.sum() / 1e6).round(0).to_dict())


if __name__ == "__main__":
    if "--so-rotulos" in sys.argv:   # reaplica os rótulos sem reprocessar os 5,6 GB
        d = rotular(pd.read_parquet(TRATADOS / "fato_ressarc_cobranca.parquet"))
        d.to_parquet(TRATADOS / "fato_ressarc_cobranca.parquet", index=False); resumo(d)
    elif "--so-uso" in sys.argv:
        uso()
    else:
        uso(); cobranca()
