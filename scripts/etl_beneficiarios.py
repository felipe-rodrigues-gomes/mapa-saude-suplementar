"""Baixa os beneficiários (ICB-024) dos meses de fim de trimestre, agrega e apaga o bruto.

Saída: dados/tratados/beneficiarios/AAAAMM.parquet
Grão: competência × operadora × UF × cobertura × contratação × faixa etária × faixa de reajuste × sexo.
Uso: python -I scripts/etl_beneficiarios.py <raiz_do_projeto>
"""
import io, sys, time, zipfile, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd

RAIZ = Path(sys.argv[1])
BASE = "https://dadosabertos.ans.gov.br/FTP/PDA/informacoes_consolidadas_de_beneficiarios-024"
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO XX".split()
MESES = ["202112"] + [f"{a}{m:02d}" for a in range(2022, 2027) for m in (3, 6, 9, 12) if f"{a}{m:02d}" <= "202609"]
CHAVE = ["CD_OPERADORA", "SG_UF", "COBERTURA_ASSIST_PLAN", "DE_CONTRATACAO_PLANO",
         "DE_FAIXA_ETARIA", "DE_FAIXA_ETARIA_REAJ", "TP_SEXO"]
QTD = ["QT_BENEFICIARIO_ATIVO", "QT_BENEFICIARIO_ADERIDO", "QT_BENEFICIARIO_CANCELADO"]
TMP = RAIZ / "dados" / "brutos" / "_tmp_benef"
SAIDA = RAIZ / "dados" / "tratados" / "beneficiarios"
LOG = RAIZ / "dados" / "tratados" / "beneficiarios_log.txt"


def log(msg):
    linha = f"{time.strftime('%H:%M:%S')} {msg}"
    print(linha, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def baixar(url, destino, tentativas=4):
    for t in range(tentativas):
        try:
            urllib.request.urlretrieve(url, destino)
            return True
        except Exception as e:  # 404 = UF sem arquivo no mês
            if "404" in str(e):
                return False
            time.sleep(10 * (t + 1))
    raise RuntimeError(f"falha ao baixar {url}")


def processar_uf(mes, uf):
    nome = f"pda-024-icb-{uf}-{mes[:4]}_{mes[4:]}.zip"
    z = TMP / nome
    if not baixar(f"{BASE}/{mes}/{nome}", z):
        return None
    zf = zipfile.ZipFile(z)
    membro = zf.namelist()[0]
    with zf.open(membro) as f:
        amostra = f.read(2_000_000)
    try:
        amostra.decode("utf-8"); enc = "utf-8"
    except UnicodeDecodeError:
        enc = "latin-1"
    partes = []
    with zf.open(membro) as f:
        for ch in pd.read_csv(io.TextIOWrapper(f, encoding=enc), sep=";", dtype=str,
                              usecols=CHAVE + QTD, chunksize=1_500_000):
            for q in QTD:
                ch[q] = pd.to_numeric(ch[q], errors="coerce").fillna(0).astype("int64")
            partes.append(ch.groupby(CHAVE, dropna=False)[QTD].sum().reset_index())
    zf.close()
    z.unlink()
    df = pd.concat(partes).groupby(CHAVE, dropna=False)[QTD].sum().reset_index()
    return df


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    SAIDA.mkdir(parents=True, exist_ok=True)
    for mes in MESES:
        alvo = SAIDA / f"{mes}.parquet"
        if alvo.exists():
            log(f"{mes} já feito")
            continue
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=4) as ex:
            res = list(ex.map(lambda uf: processar_uf(mes, uf), UFS))
        faltando = [uf for uf, r in zip(UFS, res) if r is None]
        df = pd.concat([r for r in res if r is not None])
        df.insert(0, "COMPETENCIA", mes)
        df.to_parquet(alvo, index=False)
        log(f"{mes} ok: {len(df):,} linhas, {df.QT_BENEFICIARIO_ATIVO.sum():,} ativos, "
            f"{time.time() - t0:.0f}s, UFs sem arquivo: {faltando}")
    log("FIM")


if __name__ == "__main__":
    main()
