"""Checa cobertura e consistência das demonstrações contábeis por trimestre."""
import sys, zipfile, io, re
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
PASTA = Path(sys.argv[1])
CONTAS = {"311", "41", "3111", "411", "46"}


def ler(z: Path) -> pd.DataFrame:
    zf = zipfile.ZipFile(z)
    df = pd.read_csv(io.BytesIO(zf.read(zf.namelist()[0])), sep=";", dtype=str)
    df = df[df.CD_CONTA_CONTABIL.isin(CONTAS)].copy()
    for c in ("VL_SALDO_INICIAL", "VL_SALDO_FINAL"):
        df[c] = pd.to_numeric(df[c].str.replace(".", "", regex=False).str.replace(",", "."), errors="coerce")
    m = re.match(r"(\d)T(\d{4})", z.stem)
    df["TRI"] = int(m.group(1)); df["ANO"] = int(m.group(2))
    return df


d = pd.concat([ler(z) for z in sorted(PASTA.glob("*T20*.zip"))])
d["FLUXO"] = d.VL_SALDO_FINAL - d.VL_SALDO_INICIAL
p = d.pivot_table(index=["ANO", "TRI", "REG_ANS"], columns="CD_CONTA_CONTABIL",
                  values=["VL_SALDO_FINAL", "FLUXO", "VL_SALDO_INICIAL"], aggfunc="sum")

res = []
for (ano, tri), g in p.groupby(level=[0, 1]):
    com311 = g[("VL_SALDO_FINAL", "311")].fillna(0) > 0
    res.append(dict(ano=ano, tri=tri, operadoras_arquivo=len(g), com_contraprest=int(com311.sum()),
                    contraprest_acum_bi=g[("VL_SALDO_FINAL", "311")].sum() / 1e9,
                    eventos_acum_bi=g[("VL_SALDO_FINAL", "41")].sum() / 1e9,
                    sinist_acum=g[("VL_SALDO_FINAL", "41")].sum() / g[("VL_SALDO_FINAL", "311")].sum(),
                    sinist_tri=g[("FLUXO", "41")].sum() / g[("FLUXO", "311")].sum(),
                    ini_311_zero=int((g[("VL_SALDO_INICIAL", "311")].fillna(0) == 0).sum())))
r = pd.DataFrame(res)
print(r.round(3).to_string(index=False))

# consistência: saldo inicial do trimestre T == saldo final do trimestre T-1 (mesmo ano)?
print("\nConsistência saldo_inicial(T) x saldo_final(T-1), conta 311, mesmo ano:")
f = p[("VL_SALDO_FINAL", "311")].rename("fim").reset_index()
i = p[("VL_SALDO_INICIAL", "311")].rename("ini").reset_index()
f.columns = ["ANO", "TRI", "REG_ANS", "fim"]; i.columns = ["ANO", "TRI", "REG_ANS", "ini"]
f["TRI"] += 1
m = i.merge(f, on=["ANO", "TRI", "REG_ANS"], how="inner")
m["dif"] = (m.ini - m.fim).abs()
print(m.groupby(["ANO", "TRI"]).apply(lambda x: pd.Series({"pares": len(x), "iguais_%": (x.dif < 1).mean() * 100})).round(1).to_string())

# operadoras que somem do 2T2026 mas estavam no 1T2026
a = set(p.loc[(2026, 1)].index); b = set(p.loc[(2026, 2)].index); c = set(p.loc[(2025, 4)].index)
print(f"\n1T26 sem 2T26: {len(a - b)} | 4T25 sem 1T26: {len(c - a)} | 4T25 sem 2T26: {len(c - b)}")
