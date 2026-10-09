"""Utilidades compartidas por los scripts de descarga.

Formato de los archivos de datos (data/<capa>/<año>.json):
  {
    "capa": "aod" | "bdns" | "iati",
    "anio": 2015,
    "cols": ["id", "f", ...],          # nombres de columna (ver CAMPOS)
    "dict": {"pn": ["Perú", ...], ...},  # columnas codificadas como índice en una lista
    "rows": [[...], [...]]
  }
Así cada año es un archivo pequeño y repetir textos (país, ministerio...) no ocupa espacio.
"""
import gzip
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = "subvencionesTracker/1.0 (+https://github.com/jsn841/subvencionesTracker)"

# Columnas comunes a todas las capas. El significado exacto de cada importe
# depende de la capa y se explica en la web y en metodologia.html.
CAMPOS = [
    "id",    # identificador único dentro de la web
    "ref",   # identificador oficial en la fuente
    "f",     # fecha (AAAA-MM-DD) si la fuente la da
    "a",     # año
    "t",     # título oficial
    "b",     # beneficiario / entidad receptora / canal
    "bt",    # tipo de beneficiario o canal
    "p",     # código de país (ISO3) o código de agrupación
    "pn",    # nombre del país o agrupación, en español
    "r",     # región
    "adm",   # nivel de administración que concede
    "org",   # ministerio u organismo
    "org2",  # órgano o agencia
    "ins",   # instrumento (donación, préstamo, subvención...)
    "mod",   # modalidad / tipo de ayuda
    "cat",   # categoría estadística (AOD, otros flujos oficiales...)
    "sec",   # sector
    "imp",   # importe principal en euros (desembolso o concesión)
    "imp2",  # importe secundario en euros (compromiso o ayuda equivalente)
    "usd",   # importe principal en dólares, tal como lo publica la fuente
    "usd2",  # importe secundario en dólares
    "url",   # enlace al registro o a la consulta oficial
    "crit",  # criterio por el que el registro entra en la web
    "nota",  # observaciones
    "gob",   # partidos del gobierno que concedía en esa fecha (ver scripts/gobiernos.py)
    "gobp",  # partido de quien presidía ese gobierno
    "gobn",  # descripción del gobierno (presidente/a, periodo, fecha verificada o no)
]
DICT_COLS = {"bt", "p", "pn", "r", "adm", "org", "org2", "ins", "mod", "cat", "sec", "crit", "b", "gob", "gobp", "gobn"}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def http_get(url, headers=None, timeout=900, retries=5, pause=20, ok_404=False):
    """Descarga una URL con reintentos. Devuelve bytes, o None si ok_404 y la fuente responde 404."""
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip", **(headers or {})})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return body
        except urllib.error.HTTPError as e:
            if e.code == 404 and ok_404:
                return None
            last = e
            # 429 / 5xx: esperar más
            wait = pause * (i + 1) * (3 if e.code == 429 else 1)
            log(f"  HTTP {e.code} en {url[:120]} — reintento en {wait}s")
            time.sleep(wait)
        except Exception as e:  # red, timeout...
            last = e
            log(f"  error {e!r} en {url[:120]} — reintento en {pause * (i + 1)}s")
            time.sleep(pause * (i + 1))
    raise RuntimeError(f"No se pudo descargar {url}: {last}")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def year_path(capa, anio):
    return os.path.join(DATA, capa, f"{anio}.json")


def write_year(capa, anio, records):
    """Escribe los registros (lista de dicts) de un año en formato compacto."""
    os.makedirs(os.path.join(DATA, capa), exist_ok=True)
    records = sorted(records, key=lambda r: (-(r.get("imp") or r.get("usd") or 0), r["id"]))
    dicts = {c: [] for c in CAMPOS if c in DICT_COLS}
    index = {c: {} for c in dicts}
    rows = []
    for rec in records:
        row = []
        for c in CAMPOS:
            v = rec.get(c)
            if isinstance(v, float):
                v = round(v, 2)
            if c in dicts:
                v = "" if v is None else str(v)
                if v not in index[c]:
                    index[c][v] = len(dicts[c])
                    dicts[c].append(v)
                v = index[c][v]
            elif v is None:
                v = ""
            row.append(v)
        rows.append(row)
    out = {"capa": capa, "anio": anio, "cols": CAMPOS, "dict": dicts, "rows": rows}
    with open(year_path(capa, anio), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))


def read_year(capa, anio):
    """Lee un archivo de año y devuelve la lista de dicts (o [] si no existe)."""
    path = year_path(capa, anio)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    cols, dicts = d["cols"], d["dict"]
    recs = []
    for row in d["rows"]:
        rec = {}
        for c, v in zip(cols, row):
            if c in dicts:
                v = dicts[c][v]
            rec[c] = v if v != "" else None
        recs.append(rec)
    return recs


def load_state():
    path = os.path.join(DATA, "estado.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "estado.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1, sort_keys=True)
