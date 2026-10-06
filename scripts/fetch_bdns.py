"""Descarga de la BDNS (infosubvenciones.es) las concesiones destinadas al exterior.

Criterios de selección (se guardan en cada registro, campo "crit"):
  1. Concesiones de convocatorias cuya región de impacto está fuera de España
     (países de la UE, "Regiones o países no europeos" o "Todo el mundo").
  2. Concesiones de convocatorias con finalidad "Cooperación internacional para el desarrollo y cultural".

La consulta pública de la BDNS solo muestra las concesiones de los últimos cuatro años.
Por eso este script NO borra nada: añade lo nuevo, actualiza lo que la fuente haya corregido y
conserva lo que ya no se ve en la consulta (con una nota), de modo que el archivo crece con el tiempo.

Privacidad: cuando el beneficiario es una persona física (la BDNS enmascara su NIF), no se publica su nombre.
"""
import json
import os
import re
import time
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from common import DATA, http_get, log, now_iso, load_state, save_state, read_year, write_year
import traducciones as T

API = "https://www.infosubvenciones.es/bdnstrans/api"
WEB_CONV = "https://www.infosubvenciones.es/bdnstrans/GE/es/convocatorias/{}"
FINALIDAD_COOPERACION = 20
PAGE = 10000

NUTS_ISO2 = {"EL": "GR", "UK": "GB"}
ADMIN = {"ESTADO": T.AGE, "AUTONOMICA": T.CCAA, "LOCAL": T.EELL, "OTROS": T.OTROS}
INSTRUMENTOS = {
    "SUBVENCIÓN Y ENTREGA DINERARIA SIN CONTRAPRESTACIÓN": "Subvención",
    "PRÉSTAMO": "Préstamo",
    "GARANTÍA": "Garantía",
    "VENTAJA FISCAL": "Ventaja fiscal",
    "APORTACIÓN DE FINANCIACIÓN RIESGO": "Aportación de financiación de riesgo",
    "OTROS INSTRUMENTOS DE AYUDA": "Otros instrumentos de ayuda",
}


def api_json(path, params):
    url = f"{API}/{path}?" + urllib.parse.urlencode(params, doseq=True)
    for intento in range(8):
        body = http_get(url, retries=4, pause=30)
        j = json.loads(body)
        if isinstance(j, dict) and j.get("codigo") == "ERR_MANTENIMIENTO_BBDD":
            espera = 120 * (intento + 1)
            log(f"  BDNS en mantenimiento; reintento en {espera}s")
            time.sleep(espera)
            continue
        return j
    raise RuntimeError("La BDNS sigue en mantenimiento; se reintentará en la próxima ejecución.")


def concesiones(params):
    page, out = 0, []
    while True:
        j = api_json("concesiones/busqueda", {**params, "page": page, "pageSize": PAGE, "vpd": "GE",
                                              "order": "fechaConcesion", "direccion": "asc"})
        if "content" not in j:
            raise RuntimeError(f"Respuesta inesperada de la BDNS: {str(j)[:300]}")
        out.extend(j["content"])
        if j.get("last", True) or not j["content"]:
            return out
        page += 1
        time.sleep(2)


def regiones_exteriores():
    """Regiones de primer nivel que no son España: [(id, codigo, nombre)]."""
    out = []
    for r in api_json("regiones", {}):
        desc = r["descripcion"].strip()
        cod, _, nombre = desc.partition(" - ")
        if cod.strip() != "ES":
            out.append((r["id"], cod.strip(), nombre.strip()))
    return out


def pais_de_region(cod, nombre):
    if cod == "XXX":
        return "XNE", "Fuera de Europa (país no especificado en la fuente)", "Fuera de Europa"
    if cod == "XXXX":
        return "XWW", "Todo el mundo (país no especificado en la fuente)", "Todo el mundo"
    iso3 = T.iso2_a_iso3(NUTS_ISO2.get(cod, cod))
    return (iso3 or cod), T.pais_es(iso3, nombre.title()) if iso3 else nombre.title(), "Europa"


def separar_beneficiario(texto):
    """'G12345678 NOMBRE' -> (identificador, nombre, es_persona_fisica)."""
    texto = (texto or "").strip()
    ident, _, nombre = texto.partition(" ")
    if not nombre:
        return "", texto, False
    persona = "*" in ident
    return ident, nombre.strip(), persona


def convocatoria_info(cache, num):
    if num in cache:
        return cache[num]
    try:
        j = api_json("convocatorias", {"vpd": "GE", "numConv": num})
        info = {
            "finalidad": j.get("descripcionFinalidad"),
            "tipo": j.get("tipoConvocatoria"),
            "regiones": [r.get("descripcion") for r in j.get("regiones") or []],
            "beneficiarios": [b.get("descripcion") for b in j.get("tiposBeneficiarios") or []],
        }
    except Exception as e:  # noqa: BLE001
        log(f"  convocatoria {num}: {e}")
        info = None
    cache[num] = info
    time.sleep(0.5)
    return info


def main():
    hoy = date.today().isoformat()
    state = load_state()
    st = state.setdefault("bdns", {})
    os.makedirs(os.path.join(DATA, "bdns"), exist_ok=True)
    cache_path = os.path.join(DATA, "bdns", "_convocatorias.json")
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}

    # 1) Descarga según los dos criterios
    encontrados = {}  # id -> (concesion, [criterios], (p, pn, r))
    for rid, cod, nombre in regiones_exteriores():
        lista = concesiones({"regiones": rid})
        log(f"Región {cod} {nombre}: {len(lista)} concesiones")
        for c in lista:
            e = encontrados.setdefault(c["id"], [c, [], None])
            e[1].append(f"Región de impacto: {nombre.title() if cod not in ('XXX', 'XXXX') else nombre}")
            ubic = pais_de_region(cod, nombre)
            if e[2] is None or e[2][0] in ("XNE", "XWW"):
                e[2] = ubic
        time.sleep(2)
    lista = concesiones({"finalidad": FINALIDAD_COOPERACION})
    log(f"Finalidad cooperación internacional: {len(lista)} concesiones")
    for c in lista:
        e = encontrados.setdefault(c["id"], [c, [], None])
        e[1].append("Finalidad: Cooperación internacional para el desarrollo y cultural")

    # 2) Datos de cada convocatoria (finalidad, tipo, beneficiarios), con caché y 4 consultas en paralelo
    pendientes = sorted({str(c.get("numeroConvocatoria")) for c, _, _ in encontrados.values() if c.get("numeroConvocatoria")} - set(cache))
    log(f"Convocatorias nuevas a consultar: {len(pendientes)}")
    with ThreadPoolExecutor(max_workers=4) as ex:
        for k, _ in enumerate(ex.map(lambda n: convocatoria_info(cache, n), pendientes)):
            if k and k % 500 == 0:
                log(f"  {k} convocatorias consultadas")

    # 3) Convierte al formato común
    nuevos = {}
    for cid, (c, crits, ubic) in encontrados.items():
        num = str(c.get("numeroConvocatoria") or "")
        info = cache.get(num) if num else None
        ident, nombre, persona = separar_beneficiario(c.get("beneficiario"))
        p, pn, r = ubic or ("XUN", "País no especificado en la fuente", "Sin especificar")
        fecha = c.get("fechaConcesion") or ""
        tipos_benef = ", ".join((info or {}).get("beneficiarios") or []) or None
        nuevos[f"bdns-{cid}"] = {
            "id": f"bdns-{cid}",
            "ref": c.get("codConcesion"),
            "f": fecha or None,
            "a": int(fecha[:4]) if fecha[:4].isdigit() else None,
            "t": (c.get("convocatoria") or "").strip(),
            "b": "Persona física (nombre no publicado en esta web)" if persona else nombre,
            "bt": "Persona física" if persona else (tipos_benef or "No informado"),
            "p": p, "pn": pn, "r": r,
            "adm": ADMIN.get(c.get("nivel1"), c.get("nivel1") or T.OTROS),
            "org": c.get("nivel2"),
            "org2": c.get("nivel3"),
            "ins": INSTRUMENTOS.get((c.get("instrumento") or "").strip().upper(), (c.get("instrumento") or "").strip().capitalize() or None),
            "mod": (info or {}).get("tipo"),
            "cat": "Concesión registrada en la BDNS",
            "sec": ((info or {}).get("finalidad") or "").capitalize() or None,
            "imp": c.get("importe"),
            "imp2": c.get("ayudaEquivalente"),
            "usd": None, "usd2": None,
            "url": WEB_CONV.format(num) if num else None,
            "crit": " · ".join(sorted(set(crits))),
            "nota": None if persona or not ident else f"Identificador del beneficiario en la BDNS: {ident}",
        }

    # 4) Fusión con lo ya guardado (nunca se borra)
    por_anio = defaultdict(dict)
    for fn in os.listdir(os.path.join(DATA, "bdns")):
        if re.fullmatch(r"\d{4}\.json", fn):
            for rec in read_year("bdns", int(fn[:4])):
                por_anio[rec["a"]][rec["id"]] = rec
    previos = {rid for d in por_anio.values() for rid in d}
    altas = 0
    for rid, rec in nuevos.items():
        if rid not in previos:
            altas += 1
        for d in por_anio.values():  # si cambió de año por una corrección
            d.pop(rid, None)
        por_anio[rec["a"]][rid] = rec
    retirados = 0
    for d in por_anio.values():
        for rid, rec in d.items():
            if rid not in nuevos:
                retirados += 1
                aviso = "Ya no aparece en la consulta pública de la BDNS"
                if not (rec.get("nota") or "").startswith(aviso):
                    rec["nota"] = f"{aviso} (comprobado el {hoy})." + (f" {rec['nota']}" if rec.get("nota") else "")
    for anio, d in por_anio.items():
        if anio:
            write_year("bdns", anio, list(d.values()))
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, separators=(",", ":"))

    st.update({"ultima_comprobacion": now_iso(), "en_fuente": len(nuevos), "altas_ultima": altas,
               "fuera_de_consulta": retirados})
    save_state(state)
    log(f"BDNS: {len(nuevos)} en la fuente, {altas} nuevas, {retirados} conservadas que ya no aparecen")


if __name__ == "__main__":
    main()
