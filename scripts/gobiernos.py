"""Asigna a cada registro el gobierno que estaba en el cargo en la fecha de la ayuda.

Fuente: datos-manuales/gobiernos.csv (periodos de gobierno con su fuente). La regla es sencilla y
comprobable: cuenta el gobierno que había tomado posesión en la fecha de concesión; mientras un
gobierno está en funciones, se asigna al saliente. Si la fuente solo da el año y ese año hubo
cambio de gobierno, se indica «Cambio de gobierno en el año» sin repartir el importe.

Campos que añade a cada registro:
  gob   partidos del gobierno, p. ej. «PP + Vox» (o una categoría como «No aplica»)
  gobp  partido de quien preside el gobierno, p. ej. «PP»
  gobn  descripción: ámbito, presidente/a, periodo y si la fecha está verificada
"""
import csv
import os
import re
import unicodedata
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, "datos-manuales", "gobiernos.csv")

NO_APLICA = "No aplica (organismo que no depende de un gobierno)"
LOCAL = "Gobierno local (pendiente de incorporar)"
NO_IDENT = "No identificable en la fuente"
SIN_DATOS = "Sin datos de gobierno para esa fecha"
CAMBIO = "Cambio de gobierno en el año"

# Palabras clave (sin tildes, en minúsculas) para reconocer cada comunidad en los nombres de las fuentes.
# El orden importa: «castilla-la mancha» antes que «castilla y leon».
CLAVES = [
    ("CM", ("castilla-la mancha", "castilla la mancha")),
    ("CL", ("castilla y leon",)),
    ("AN", ("andalucia",)),
    ("AR", ("aragon",)),
    ("AS", ("asturias",)),
    ("IB", ("balears", "baleares")),
    ("CN", ("canarias",)),
    ("CB", ("cantabria",)),
    ("CT", ("cataluna", "catalunya")),
    ("VC", ("valenciana",)),
    ("EX", ("extremadura",)),
    ("GA", ("galicia",)),
    ("RI", ("rioja",)),
    ("MD", ("madrid",)),
    ("MC", ("murcia",)),
    ("NC", ("navarra",)),
    ("PV", ("pais vasco", "euskadi")),
    ("CE", ("ceuta",)),
    ("ML", ("melilla",)),
]


def _norm(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower()).strip()


def _fecha(s):
    return date.fromisoformat(s) if s else None


def _fmt(d):
    return d.strftime("%d-%m-%Y") if d else "actualidad"


def cargar():
    periodos = {}
    with open(CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            periodos.setdefault(r["ambito_codigo"], []).append({
                "ambito": r["ambito"],
                "desde": _fecha(r["desde"]),
                "hasta": _fecha(r["hasta"]),
                "presidente": r["presidente"],
                "partido": r["partido_presidente"],
                "partidos": " + ".join(p.strip() for p in r["partidos_gobierno"].split(";") if p.strip()),
                "verificada": r["fecha_verificada"] == "sí",
            })
    for v in periodos.values():
        v.sort(key=lambda p: p["desde"])
    return periodos


PERIODOS = cargar()


def _describe(p):
    ver = "fecha verificada" if p["verificada"] else "fecha sin verificar"
    hasta = f"hasta el {_fmt(p['hasta'])}" if p["hasta"] else "hasta la actualidad"
    return f"{p['ambito']} · {p['presidente']} ({p['partido']}) · desde el {_fmt(p['desde'])} {hasta} · {ver}"


def en_fecha(codigo, d):
    """Periodo de gobierno vigente en la fecha d (date), o None."""
    for p in PERIODOS.get(codigo, []):
        if p["desde"] <= d and (p["hasta"] is None or d < p["hasta"]):
            return p
    return None


def en_anio(codigo, anio):
    """Periodos de gobierno que estuvieron en el cargo en algún momento del año."""
    ini, fin = date(anio, 1, 1), date(anio, 12, 31)
    return [p for p in PERIODOS.get(codigo, []) if p["desde"] <= fin and (p["hasta"] is None or p["hasta"] > ini)]


def comunidad(nombre):
    n = _norm(nombre)
    for codigo, claves in CLAVES:
        if any(c in n for c in claves):
            return codigo
    return None


def asignar(codigo, fecha=None, anio=None):
    """Devuelve (gob, gobp, gobn) para un ámbito en una fecha (preferente) o un año."""
    if fecha:
        p = en_fecha(codigo, date.fromisoformat(fecha[:10]))
        return (p["partidos"], p["partido"], _describe(p)) if p else (SIN_DATOS, SIN_DATOS, None)
    ps = en_anio(codigo, anio)
    if not ps or ps[0]["desde"] > date(anio, 1, 1):
        return SIN_DATOS, SIN_DATOS, None  # la tabla no cubre el año completo
    desc = " → ".join(_describe(p) for p in ps)
    gob = ps[0]["partidos"] if len({p["partidos"] for p in ps}) == 1 else CAMBIO
    gobp = ps[0]["partido"] if len({p["partido"] for p in ps}) == 1 else CAMBIO
    return gob, gobp, desc


def para_registro(capa, rec):
    """Calcula (gob, gobp, gobn) de un registro de cualquier capa."""
    adm, org = rec.get("adm") or "", rec.get("org") or ""
    fecha, anio = rec.get("f"), rec.get("a")
    if adm == "Administración General del Estado":
        return asignar("ES", fecha, anio)
    if adm == "Comunidades autónomas":
        codigo = comunidad(org)
        if not codigo:
            return NO_IDENT, NO_IDENT, "La fuente agrupa varias comunidades autónomas sin identificar cuál concede"
        return asignar(codigo, fecha, anio)
    if adm == "Entidades locales":
        if capa == "bdns" and comunidad(org) in ("CE", "ML") and "ciudad" in _norm(org):
            return asignar(comunidad(org), fecha, anio)
        return (LOCAL, LOCAL, None) if capa == "bdns" else (NO_IDENT, NO_IDENT, "La fuente agrupa a todas las entidades locales")
    if capa == "aod":
        return NO_IDENT, NO_IDENT, "La fuente no identifica a la administración concreta"
    return NO_APLICA, NO_APLICA, None
