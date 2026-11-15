"""Funções comuns do ETL."""
import io, sys, zipfile
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
BRUTOS = RAIZ / "dados" / "brutos"
TRATADOS = RAIZ / "dados" / "tratados"
TRATADOS.mkdir(parents=True, exist_ok=True)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def reg(s: pd.Series) -> pd.Series:
    """Registro ANS como texto de 6 dígitos."""
    return s.astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(6)


def num_br(s: pd.Series) -> pd.Series:
    """'1.234,56' ou '1234,56' -> float. 'ND'/vazio -> NaN."""
    s = s.astype(str).str.strip()
    tem_virgula = s.str.contains(",", regex=False)
    s = s.where(~tem_virgula, s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    return pd.to_numeric(s, errors="coerce")


def ler_csv(caminho, **kw) -> pd.DataFrame:
    for enc in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(caminho, sep=";", dtype=str, encoding=enc, **kw)
        except UnicodeDecodeError:
            continue
    raise ValueError(caminho)


def ler_zip_csv(caminho, **kw) -> pd.DataFrame:
    zf = zipfile.ZipFile(caminho)
    raw = zf.read(zf.namelist()[0])
    try:
        txt = raw.decode("utf-8")
    except UnicodeDecodeError:
        txt = raw.decode("latin-1")
    return pd.read_csv(io.StringIO(txt), sep=";", dtype=str, **kw)
