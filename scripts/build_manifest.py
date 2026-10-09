"""Genera data/manifest.json: qué archivos hay, cuántos registros y qué totales tiene cada año.

La web lee este archivo primero para saber qué descargar. También sirve para comprobar
de un vistazo que la carga ha ido bien (los totales se pueden cotejar con las fuentes).
"""
import json
import os
import re
from collections import Counter

from common import DATA, load_state, now_iso, read_year, write_year
import gobiernos

CAPAS = {
    "aod": {
        "nombre": "Ayuda Oficial al Desarrollo (CRS de la OCDE)",
        "corto": "Ayuda al desarrollo (OCDE)",
        "importe": "Desembolsado",
        "importe2": "Comprometido",
        "moneda": "EUR (convertido desde USD)",
        "fuente": "OCDE · Creditor Reporting System (CRS), donante España",
    },
    "bdns": {
        "nombre": "Concesiones registradas en la BDNS (infosubvenciones.es)",
        "corto": "Concesiones BDNS",
        "importe": "Importe concedido",
        "importe2": "Ayuda equivalente",
        "moneda": "EUR",
        "fuente": "IGAE · Base de Datos Nacional de Subvenciones (SNPSAP)",
    },
    "iati": {
        "nombre": "Actividades de AECID publicadas en IATI",
        "corto": "AECID (IATI)",
        "importe": "Desembolsado",
        "importe2": "Comprometido",
        "moneda": "EUR",
        "fuente": "AECID · estándar IATI",
    },
}


def aplicar_gobiernos():
    """Añade a cada registro el gobierno que estaba en el cargo en su fecha (o año)."""
    for capa in CAPAS:
        carpeta = os.path.join(DATA, capa)
        if not os.path.isdir(carpeta):
            continue
        for fn in sorted(os.listdir(carpeta)):
            if re.fullmatch(r"\d{4}\.json", fn):
                y = int(fn[:4])
                recs = read_year(capa, y)
                for r in recs:
                    r["gob"], r["gobp"], r["gobn"] = gobiernos.para_registro(capa, r)
                write_year(capa, y, recs)


def main():
    aplicar_gobiernos()
    state = load_state()
    man = {"generado": now_iso(), "capas": {}}
    region_por_pais = Counter()
    for capa, meta in CAPAS.items():
        carpeta = os.path.join(DATA, capa)
        anios = []
        if os.path.isdir(carpeta):
            for fn in sorted(os.listdir(carpeta)):
                if not re.fullmatch(r"\d{4}\.json", fn):
                    continue
                y = int(fn[:4])
                recs = read_year(capa, y)
                if capa == "aod":
                    for r in recs:
                        if r.get("p") and r.get("r") and len(r["p"]) == 3:
                            region_por_pais[(r["p"], r["r"])] += 1
                anios.append({
                    "anio": y,
                    "archivo": f"data/{capa}/{fn}",
                    "bytes": os.path.getsize(os.path.join(carpeta, fn)),
                    "registros": len(recs),
                    "importe": round(sum(r.get("imp") or 0 for r in recs), 2),
                    "importe2": round(sum(r.get("imp2") or 0 for r in recs), 2),
                    "usd": round(sum(r.get("usd") or 0 for r in recs), 2),
                })
        man["capas"][capa] = {**meta, "anios": anios, "estado": state.get("crs" if capa == "aod" else capa, {})}
    # región más frecuente de cada país en el CRS (para colocar en el mapa/región los datos de otras capas)
    mejor = {}
    for (p, r), n in region_por_pais.most_common():
        mejor.setdefault(p, r)
    man["region_por_pais"] = mejor
    tc = os.path.join(DATA, "tipos_cambio.json")
    if os.path.exists(tc):
        man["tipos_cambio"] = json.load(open(tc, encoding="utf-8"))
    with open(os.path.join(DATA, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    for capa, c in man["capas"].items():
        print(f"{capa}: {len(c['anios'])} años, {sum(a['registros'] for a in c['anios'])} registros, "
              f"{sum(a['bytes'] for a in c['anios']) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
