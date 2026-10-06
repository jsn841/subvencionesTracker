"""Exploración de fuentes: imprime estructura de datos reales (solo diagnóstico)."""
import json, re, sys, urllib.request, urllib.parse, ssl, io, zipfile, gzip

UA = {"User-Agent": "Mozilla/5.0 (subvencionesTracker probe)", "Accept": "*/*"}

def get(url, n=None, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read() if n is None else r.read(n)
        return r.status, r.headers.get("content-type"), data

def show(title, url, n=4000, headers=None, maxbytes=None):
    print(f"\n===== {title}\n{url}")
    try:
        st, ct, d = get(url, maxbytes, headers)
        print("status", st, ct, "bytes", len(d))
        print(d[:n].decode("utf-8", "replace"))
        return d
    except Exception as e:
        print("ERROR", repr(e))
        if hasattr(e, "read"):
            try: print(e.read()[:1500].decode("utf-8","replace"))
            except Exception: pass

def links(d, pat):
    if not d: return []
    s = d.decode("utf-8", "replace")
    out = sorted(set(re.findall(r'href="([^"]+)"', s)))
    return [l for l in out if re.search(pat, l, re.I)]

part = sys.argv[1]
B = "https://www.infosubvenciones.es/bdnstrans/api"
if part == "bdns":
    for u in ["https://www.infosubvenciones.es/bdnstrans/v3/api-docs",
              "https://www.infosubvenciones.es/bdnstrans/api-docs",
              "https://www.infosubvenciones.es/bdnstrans/v2/api-docs"]:
        d = show("swagger", u, 200)
        if d and d[:1] == b"{":
            spec = json.loads(d)
            for p, ops in spec.get("paths", {}).items():
                for m, op in ops.items():
                    ps = [x.get("name") for x in op.get("parameters", [])]
                    print(m.upper(), p, ps)
            comps = spec.get("components", {}).get("schemas", spec.get("definitions", {}))
            for k, v in comps.items():
                if re.search(r"conces|ayuda|benef|organ|region|instrum|convoc", k, re.I):
                    print("SCHEMA", k, list((v.get("properties") or {}).keys()))
            break
    show("concesiones", B + "/concesiones/busqueda?page=0&pageSize=3", 6000)
    show("concesiones 2014", B + "/concesiones/busqueda?page=0&pageSize=2&fechaDesde=01/01/2014&fechaHasta=31/01/2014", 3000)
    show("organos C", B + "/organos?idAdmon=C", 3000)
    show("regiones", B + "/regiones", 3000)
    show("instrumentos", B + "/instrumentos", 2000)
    show("finalidades", B + "/finalidades", 2000)
    show("convocatoria detalle", B + "/convocatorias?numConv=800000", 3000)
elif part == "infoaod":
    for u in ["https://infoaod.maec.es/descargas/DescargasAyuda.aspx", "https://infoaod.maec.es/",
              "https://www.exteriores.gob.es/es/ServiciosAlCiudadano/Paginas/Cooperacion/Seguimiento-y-Transparencia.aspx",
              "https://www.aecid.es/w/datos-info-od", "https://infoaod-info.maec.es/"]:
        d = show("page", u, 1500)
        for l in links(d, r"volcado|descarga|xls|zip|csv|seguimiento|\.aspx"): print("  LINK", l)
elif part == "iati":
    d = show("registry aecid", "https://iatiregistry.org/api/3/action/package_search?q=organization:aecid&rows=50", 300)
    if d:
        for p in json.loads(d)["result"]["results"]:
            print(p["name"], [r["url"] for r in p["resources"]], p.get("extras") and {e["key"]: e["value"] for e in p["extras"]})
    d = show("registry ES publishers", "https://iatiregistry.org/api/3/action/organization_list?all_fields=true&limit=2000", 200)
    if d:
        for o in json.loads(d)["result"]:
            if str(o.get("publisher_country", "")).upper() == "ES" or "spain" in o.get("title","").lower() or "espa" in o.get("title","").lower():
                print("PUB", o["name"], o.get("title"), o.get("publisher_iati_id"), o.get("publisher_organization_type"), o.get("package_count"))
elif part == "crs":
    show("crs dataflow", "https://sdmx.oecd.org/public/rest/dataflow/OECD.DCD.FSD/DSD_CRS@DF_CRS/latest?references=datastructure", 300,
         headers={"Accept": "application/vnd.sdmx.structure+json;version=1.0"})
    d = None
    try:
        st, ct, d = get("https://sdmx.oecd.org/public/rest/dataflow/OECD.DCD.FSD/DSD_CRS@DF_CRS/latest?references=datastructure",
                        headers={"Accept": "application/vnd.sdmx.structure+json;version=1.0"})
        j = json.loads(d)
        for ds in j["data"]["dataStructures"]:
            print("DIMS", [x["id"] for x in ds["dataStructureComponents"]["dimensionList"]["dimensions"]])
            print("ATTRS", [x["id"] for x in ds["dataStructureComponents"].get("attributeList", {}).get("attributes", [])])
    except Exception as e:
        print("ERR", e)
