"""Descarga las actividades que AECID publica en el estándar IATI y las guarda por años.

Fuente: registro IATI (iatiregistry.org) -> ficheros XML publicados por AECID.
Cada registro de la web = una actividad en un año, con la suma de sus desembolsos (tipo 3)
y compromisos (tipo 2) de ese año, en la moneda publicada (AECID publica en euros).
Esta capa NO se suma a las otras: AECID también informa estas actividades al CRS.
"""
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

from common import DATA, http_get, log, now_iso, load_state, save_state, write_year
import traducciones as T

REGISTRY = "https://iatiregistry.org/api/3/action/package_search?q=organization:aecid&rows=100"
DPORTAL = "https://d-portal.org/ctrack.html#view=act&aid={}"

TIPO_ORG = {
    "10": "Gobierno", "11": "Gobierno local", "15": "Otro sector público", "21": "ONG internacional",
    "22": "ONG nacional", "23": "ONG regional", "24": "ONG del país socio", "30": "Alianza público-privada",
    "40": "Organismo multilateral", "60": "Fundación", "70": "Sector privado",
    "71": "Sector privado del país proveedor", "72": "Sector privado del país receptor",
    "73": "Sector privado de un tercer país", "80": "Universidad o centro de investigación", "90": "Otros",
}
REGION_IATI = {
    "89": "Europa (regional)", "189": "Norte de África (regional)", "289": "África subsahariana (regional)",
    "298": "África (regional)", "380": "Caribe (regional)", "389": "Centroamérica (regional)",
    "489": "Sudamérica (regional)", "498": "América (regional)", "589": "Oriente Medio (regional)",
    "619": "Asia central (regional)", "679": "Asia meridional (regional)", "689": "Asia meridional y central (regional)",
    "789": "Asia oriental (regional)", "798": "Asia (regional)", "889": "Oceanía (regional)",
    "998": "Países en desarrollo (sin especificar)",
}


def texto(el, path):
    n = el.find(path)
    if n is None:
        return None
    nar = n.find("narrative")
    return ((nar.text if nar is not None else n.text) or "").strip() or None


def codigo(el, path):
    n = el.find(path)
    return n.get("code") if n is not None else None


def principal(elems, attr="code"):
    """Elemento con mayor porcentaje."""
    best, bp = None, -1.0
    for e in elems:
        try:
            pct = float(e.get("percentage") or 100)
        except ValueError:
            pct = 0
        if pct > bp:
            best, bp = e, pct
    return best.get(attr) if best is not None else None


def main():
    state = load_state()
    st = state.setdefault("iati", {})
    pk = json.loads(http_get(REGISTRY))["result"]["results"]
    urls = [r["url"] for p in pk for r in p.get("resources", []) if "activity" in p["name"]]
    log(f"IATI AECID: {len(urls)} ficheros de actividades")
    por_anio = defaultdict(list)
    monedas = Counter()
    for url in urls:
        root = ET.fromstring(http_get(url))
        for act in root.findall("iati-activity"):
            ident = (act.findtext("iati-identifier") or "").strip()
            moneda_def = act.get("default-currency") or "EUR"
            titulo = texto(act, "title") or "(sin título en la fuente)"
            # receptor: organización ejecutora (rol 4) o la que más aparece en las transacciones
            receptores = Counter()
            for t in act.findall("transaction"):
                ro = t.find("receiver-org")
                if ro is not None:
                    nar = ro.find("narrative")
                    if nar is not None and nar.text:
                        receptores[(nar.text.strip(), ro.get("type"))] += 1
            if not receptores:
                for po in act.findall("participating-org"):
                    if po.get("role") in ("4", "2"):
                        nar = po.find("narrative")
                        if nar is not None and nar.text:
                            receptores[(nar.text.strip(), po.get("type"))] += 1
            (benef, btype) = receptores.most_common(1)[0][0] if receptores else ("No informado", None)
            iso2 = principal(act.findall("recipient-country"))
            if iso2:
                iso3 = T.iso2_a_iso3(iso2.upper())
                p, pn = (iso3 or iso2), T.pais_es(iso3, iso2) if iso3 else iso2
            else:
                reg = principal(act.findall("recipient-region"))
                p, pn = (f"R{reg}" if reg else "XUN"), REGION_IATI.get(reg or "", "Sin especificar")
            sector = principal([s for s in act.findall("sector") if s.get("vocabulary") in (None, "1")])
            fin, aid, flow = (codigo(act, n) for n in ("default-finance-type", "default-aid-type", "default-flow-type"))
            sumas = defaultdict(lambda: {"3": 0.0, "2": 0.0, "fechas": []})
            for t in act.findall("transaction"):
                tt = t.find("transaction-type")
                td = t.find("transaction-date")
                val = t.find("value")
                if tt is None or td is None or val is None or tt.get("code") not in ("2", "3"):
                    continue
                y = int((td.get("iso-date") or "0")[:4] or 0)
                if not y:
                    continue
                moneda = val.get("currency") or moneda_def
                monedas[moneda] += 1
                if moneda != "EUR":
                    log(f"  {ident}: transacción en {moneda}, se omite (solo se admiten euros)")
                    continue
                sumas[y][tt.get("code")] += float(val.text or 0)
                sumas[y]["fechas"].append(td.get("iso-date"))
            for y, s in sumas.items():
                por_anio[y].append({
                    "id": f"iati-{ident}-{y}",
                    "ref": ident,
                    "f": max(s["fechas"]) if s["fechas"] else None,
                    "a": y,
                    "t": titulo,
                    "b": benef,
                    "bt": TIPO_ORG.get(btype or "", "No informado"),
                    "p": p, "pn": pn, "r": None,
                    "adm": T.AGE,
                    "org": "Ministerio de Asuntos Exteriores, Unión Europea y Cooperación",
                    "org2": "Agencia Española de Cooperación Internacional para el Desarrollo (AECID)",
                    "ins": T.instrumento_crs(fin, aid, None),
                    "mod": T.MODALIDADES.get(aid or "", aid or "No informado"),
                    "cat": "Ayuda Oficial al Desarrollo (AOD)" if flow == "10" else (f"Tipo de flujo {flow}" if flow else None),
                    "sec": T.sector_es(sector),
                    "imp": round(s["3"], 2), "imp2": round(s["2"], 2),
                    "usd": None, "usd2": None,
                    "url": DPORTAL.format(ident),
                    "crit": "Publicado por AECID en IATI",
                    "nota": "La fecha es la de la última transacción del año.",
                })
    os.makedirs(os.path.join(DATA, "iati"), exist_ok=True)
    for fn in os.listdir(os.path.join(DATA, "iati")):  # IATI es una foto completa: se reescribe
        if re.fullmatch(r"\d{4}\.json", fn):
            os.remove(os.path.join(DATA, "iati", fn))
    for y, recs in por_anio.items():
        write_year("iati", y, recs)
    st.update({"ultima_comprobacion": now_iso(), "actividades": sum(len(v) for v in por_anio.values()),
               "anios": sorted(por_anio), "monedas": dict(monedas)})
    save_state(state)
    log(f"IATI: {st['actividades']} registros actividad-año en {sorted(por_anio)}")


if __name__ == "__main__":
    main()
