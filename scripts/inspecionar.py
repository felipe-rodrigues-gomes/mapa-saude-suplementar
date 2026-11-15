"""Inspeção inicial das bases brutas: dicionários, colunas, períodos."""
import sys, zipfile, io
from pathlib import Path
import pandas as pd

pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_colwidth", 80)
R = Path(sys.argv[1])  # dados/brutos


def ler_csv(caminho_ou_buf, n=None, **kw):
    for enc in ("utf-8", "latin-1"):
        try:
            if hasattr(caminho_ou_buf, "seek"):
                caminho_ou_buf.seek(0)
            return pd.read_csv(caminho_ou_buf, sep=";", nrows=n, encoding=enc, dtype=str, **kw)
        except UnicodeDecodeError:
            continue


alvo = sys.argv[2] if len(sys.argv) > 2 else "tudo"

if alvo in ("dic", "tudo"):
    for f in sorted((R / "dicionarios").glob("*.ods")):
        print(f"\n######## DICIONÁRIO {f.name}")
        for aba, df in pd.read_excel(f, engine="odf", sheet_name=None, header=None).items():
            print(f"--- aba {aba}")
            print(df.dropna(how="all").fillna("").to_string(index=False, header=False)[:6000])

if alvo in ("csv", "tudo"):
    for f in sorted(list((R / "glosa").glob("*.csv")) + list((R / "igr").glob("*.csv"))
                    + list((R / "idss").glob("*.csv")) + list((R / "cadop").glob("*.csv"))):
        df = ler_csv(f)
        print(f"\n######## {f.parent.name}/{f.name}  linhas={len(df)}")
        print(df.head(4).to_string())

if alvo in ("zip", "tudo"):
    for z in sorted((R / "contabeis").glob("*.zip")) + sorted((R / "beneficiarios").glob("*.zip")):
        with zipfile.ZipFile(z) as zf:
            for nome in zf.namelist():
                buf = io.BytesIO(zf.read(nome))
                df = ler_csv(buf)
                print(f"\n######## {z.name}/{nome}  linhas={len(df)}")
                print(df.head(4).to_string())
