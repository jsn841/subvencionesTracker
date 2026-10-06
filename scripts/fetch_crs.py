"""Descarga la ayuda de España del CRS (OCDE), proyecto a proyecto, y la guarda por años.

Fuente: API SDMX oficial de la OCDE, conjunto DSD_CRS@DF_CRS (espacio dcd-public).
  - Se piden solo los datos del donante España (ESP).
  - Se usan importes a precios corrientes (PRICE_BASE = V), en dólares, como los publica la OCDE.
  - Se añade una conversión a euros con el tipo de cambio medio anual del BCE.

Uso:
  python scripts/fetch_crs.py                 # años que faltan + últimos 3 años (la OCDE revisa datos)
  python scripts/fetch_crs.py --years 1995-2024 --force
"""
import argparse
import csv
import hashlib
import io
import json
import os
import time
from collections import defaultdict
from datetime import date

from common import DATA, http_get, log, now_iso, load_state, save_state, write_year, year_path
import traducciones as T

API = "https://sdmx.oecd.org/dcd-public/rest/data/OECD.DCD.FSD,DSD_CRS@DF_CRS,/ESP.........."
AVAIL = "https://sdmx.oecd.org/dcd-public/rest/availableconstraint/OECD.DCD.FSD,DSD_CRS@DF_CRS,/ESP........../all/TIME_PERIOD"
ECB = "https://data-api.ecb.europa.eu/service/data/EXR/A.USD.{}.SP00.A?format=csvdata"
PRIMER_ANIO = 1995  # primer año con datos proyecto a proyecto de España en la API


def tipos_cambio():
    """Dólares por euro, media anual del BCE. Antes de 1999 se usa el ECU (equivalente 1:1 al euro)."""
    tipos, fuente = {}, {}
    for moneda in ("ECU", "EUR"):
        try:
            body = http_get(ECB.format(moneda), retries=3, ok_404=True)
        except RuntimeError as e:
            log(f"  sin tipo de cambio {moneda}: {e}")
            continue
        if not body:
            continue
        for row in csv.DictReader(io.StringIO(body.decode("utf-8"))):
            try:
                y, v = int(row["TIME_PERIOD"][:4]), float(row["OBS_VALUE"])
            except (KeyError, ValueError):
                continue
            if moneda == "EUR" or y < 1999:
                tipos[y] = v
                fuente[y] = f"BCE, media anual USD/{moneda}"
    path = os.path.join(DATA, "tipos_cambio.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"descripcion": "Dólares estadounidenses por 1 euro (media anual). Antes de 1999: por 1 ECU.",
                   "tipos": {str(k): v for k, v in sorted(tipos.items())},
                   "fuente": {str(k): v for k, v in sorted(fuente.items())}}, f, ensure_ascii=False, indent=1)
    return tipos


def anios_disponibles():
    try:
        body = http_get(AVAIL, headers={"Accept": "application/vnd.sdmx.structure+json;version=1.0"}, retries=3)
        j = json.loads(body)
        rng = j["data"]["contentConstraints"][0]["cubeRegions"][0]["keyValues"][0]["timeRange"]
        return int(rng["startPeriod"]["period"][:4]), int(rng["endPeriod"]["period"][:4])
    except Exception as e:  # noqa: BLE001
        log(f"  no se pudo consultar la disponibilidad: {e}")
        return PRIMER_ANIO, date.today().year - 1


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def procesar(texto, anio, usd_por_eur):
    grupos = {}
    for row in csv.DictReader(io.StringIO(texto)):
        if row.get("MD_DIM") != "DD" or row.get("PRICE_BASE") != "V":
            continue
        clave = tuple(row.get(k, "") for k in (
            "OECD_ID", "DONOR_PROJECT_ID", "RECIPIENT", "SECTOR", "MEASURE", "CHANNEL", "MODALITY",
            "DONOR_AGENCY", "CHANNELDELIVERY_CODE", "CHANNELDELIVERY_NAME", "PROJECT_TITLE",
            "SHORT_DESCRIPTION", "FINANCETYPE_CODE", "CATEGORY_CODE"))
        g = grupos.get(clave)
        if g is None:
            g = grupos[clave] = {"row": row, "D": 0.0, "C": 0.0, "md": []}
        mult = 10 ** int(num(row.get("UNIT_MULT")) or 0)
        g[row.get("FLOW_TYPE")] = g.get(row.get("FLOW_TYPE"), 0.0) + num(row.get("OBS_VALUE")) * mult
        g["md"].append(row.get("MD_ID", ""))

    rate = usd_por_eur.get(anio)
    nuevos_agencia = set()
    recs = []
    for clave, g in grupos.items():
        row = g["row"]
        adm, org = T.agencia(row.get("DONOR_AGENCY"))
        if row.get("DONOR_AGENCY") and row.get("DONOR_AGENCY") not in T.AGENCIAS:
            nuevos_agencia.add(row.get("DONOR_AGENCY"))
        rec_code = row.get("RECIPIENT", "")
        rec_label = row.get("Recipient") or rec_code
        pn = T.pais_es(rec_code, None) if len(rec_code) == 3 and rec_code.isalpha() else None
        pn = pn or T.agrupacion_es(rec_label) or rec_label
        canal_nombre = row.get("CHANNELDELIVERY_NAME") or ""
        usd_d, usd_c = round(g.get("D", 0.0), 2), round(g.get("C", 0.0), 2)
        h = hashlib.sha1("|".join(clave).encode()).hexdigest()[:10]
        titulo = (row.get("PROJECT_TITLE") or row.get("SHORT_DESCRIPTION") or "").strip()
        recs.append({
            "id": h,
            "ref": " · ".join(x for x in (f"CRS {row.get('OECD_ID')}" if row.get("OECD_ID") else "",
                                          f"proyecto {row.get('DONOR_PROJECT_ID')}" if row.get("DONOR_PROJECT_ID") else "") if x),
            "f": None,
            "a": anio,
            "t": titulo or "(sin título en la fuente)",
            "b": T.CANAL_NOMBRE.get(canal_nombre, canal_nombre) or "No informado",
            "bt": T.CANALES.get(row.get("CHANNEL", ""), row.get("Channel") or "No informado"),
            "p": rec_code,
            "pn": pn,
            "r": T.REGIONES.get(row.get("REGION", ""), row.get("REGION") or "Sin especificar"),
            "adm": adm,
            "org": org,
            "org2": None,
            "ins": T.instrumento_crs(row.get("FINANCETYPE_CODE"), row.get("MODALITY"), row.get("MEASURE")),
            "mod": T.MODALIDADES.get(row.get("MODALITY", ""), row.get("Modality") or "No informado"),
            "cat": T.CATEGORIAS.get(row.get("CATEGORY_CODE", ""), row.get("CATEGORY_NAME") or ""),
            "sec": T.sector_es(row.get("SECTOR"), row.get("Sector")),
            "usd": usd_d,
            "usd2": usd_c,
            "imp": round(usd_d / rate, 2) if rate else None,
            "imp2": round(usd_c / rate, 2) if rate else None,
            "url": "+".join(sorted(set(m for m in g["md"] if m))),
            "crit": "Donante: España (CRS)",
            "nota": None,
        })
    return recs, nuevos_agencia


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", help="rango, p.ej. 1995-2024")
    ap.add_argument("--force", action="store_true", help="volver a descargar aunque el año exista")
    ap.add_argument("--pausa", type=int, default=65, help="segundos entre peticiones (límite OCDE: 60/hora)")
    args = ap.parse_args()

    state = load_state()
    st = state.setdefault("crs", {"anios": {}})
    usd_por_eur = tipos_cambio()
    ini, fin = anios_disponibles()
    log(f"CRS disponible en la API: {ini}-{fin}")
    if args.years:
        a, b = args.years.split("-")
        anios = list(range(int(a), int(b) + 1))
    else:
        anios = [y for y in range(ini, fin + 1) if args.force or not os.path.exists(year_path("aod", y)) or y > fin - 3]
    agencias_nuevas = set()
    for i, y in enumerate(anios):
        if i:
            time.sleep(args.pausa)
        log(f"CRS {y}…")
        body = http_get(f"{API}?startPeriod={y}&endPeriod={y}&format=csvfilewithlabels", ok_404=True, pause=70)
        if body is None:
            log(f"  {y}: la API responde 'sin registros'")
            st["anios"][str(y)] = {"estado": "sin datos en la API", "comprobado": now_iso()}
            continue
        recs, nuevas = procesar(body.decode("utf-8-sig"), y, usd_por_eur)
        agencias_nuevas |= nuevas
        write_year("aod", y, recs)
        st["anios"][str(y)] = {"estado": "ok", "registros": len(recs), "comprobado": now_iso(),
                               "usd_desembolsado": round(sum(r["usd"] for r in recs), 2)}
        log(f"  {y}: {len(recs)} registros")
        save_state(state)
    if agencias_nuevas:
        log("Organismos sin traducción (se muestran tal cual):", sorted(agencias_nuevas))
    st["ultima_comprobacion"] = now_iso()
    st["rango_api"] = [ini, fin]
    save_state(state)


if __name__ == "__main__":
    main()
