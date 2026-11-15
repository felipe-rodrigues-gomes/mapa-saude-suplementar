"""População IBGE -> dim_municipio.parquet

Fonte: SIDRA tabela 6579 (estimativas da população residente em 1º de julho).
Só 2024–2026: as estimativas de 2024 em diante já incorporam o ajuste de cobertura do Censo 2022.
A de 2021 é pré-Censo (213,3 mi) e o Censo 2022 publicado sem ajuste dá 203,1 mi;
misturar as três bases cria um salto artificial na taxa de cobertura.
Chave com a ANS: código IBGE de 6 dígitos (a ANS não usa o dígito verificador).
Consultas usadas (salvas em dados/brutos/ibge):
  https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/2021,2024,2025,2026
"""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *
from etl_cadastro import REGIAO

d = json.load(open(BRUTOS / "ibge" / "pop_mun_6579.json", encoding="utf-8"))[1:]
p = pd.DataFrame(d)
p = p[p.D3C.isin(["2024", "2025", "2026"])]
p["POP"] = pd.to_numeric(p.V, errors="coerce")
w = p.pivot_table(index=["D1C", "D1N"], columns="D3C", values="POP").reset_index()
w.columns = ["COD_IBGE7", "NOME_UF", "POP_2024", "POP_2025", "POP_2026"]
w["COD_MUNICIPIO"] = w.COD_IBGE7.str[:6]
w["MUNICIPIO"] = w.NOME_UF.str.rsplit(" - ", n=1).str[0]
w["UF"] = w.NOME_UF.str.rsplit(" - ", n=1).str[1]
w["REGIAO"] = w.UF.map(REGIAO)
w = w[["COD_MUNICIPIO", "COD_IBGE7", "MUNICIPIO", "UF", "REGIAO", "POP_2024", "POP_2025", "POP_2026"]]
assert not w.COD_MUNICIPIO.duplicated().any()
w.to_parquet(TRATADOS / "dim_municipio.parquet", index=False)
print(f"dim_municipio: {len(w)} municípios | Brasil 2026: {w.POP_2026.sum():,.0f} | sem população: {w.POP_2026.isna().sum()}")
print(w.groupby("UF")[["POP_2026"]].sum().T.astype(int).to_string())
