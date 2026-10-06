import json, sys, urllib.request, time, csv, io, collections
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) subvencionesTracker"}
def get(url, timeout=900, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()
def p(*a): print(*a, flush=True)
for u in ["https://data-api.ecb.europa.eu/service/data/EXR/A.USD.EUR.SP00.A?format=csvdata",
          "https://sdmx.oecd.org/public/rest/dataflow/all/DSD_EXR@DF_EXR/latest",
          "https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_EXR@DF_EXR,/ESP.A.....?format=csvfilewithlabels",
          "https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_EXR@DF_EXR,/ESP......?format=csvfilewithlabels",
          "https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_EXR@DF_EXR,1.0/ESP.A.EXC_A.......?format=csvfilewithlabels",
          "https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_EXR@DF_EXR,/ESP?format=csvfilewithlabels"]:
    try:
        d = get(u).decode("utf-8", "replace"); p("OK", u, len(d)); p(d[:1200]); p("..."); p(d[-600:])
    except Exception as e: p("ERR", u, str(e)[:200])
    time.sleep(2)
base = "https://sdmx.oecd.org/dcd-public/rest/data/OECD.DCD.FSD,DSD_CRS@DF_CRS,/ESP.........."
for yr in (2022, 2023, 2024, 1995):
    for extra in ["&format=csvfile", "&format=csvfile&dimensionAtObservation=AllDimensions"]:
        try:
            t0 = time.time(); d = get(f"{base}?startPeriod={yr}&endPeriod={yr}{extra}"); p("CRS", yr, extra, len(d), round(time.time()-t0)); break
        except Exception as e:
            p("CRSERR", yr, extra, e, getattr(e, "read", lambda: b"")()[:300])
        time.sleep(3)
# 2022 split by price base / flow
for key in ["ESP.......V....", "ESP......D.V...", "ESP......D.V.DD.."]:
    try: d = get(f"https://sdmx.oecd.org/dcd-public/rest/data/OECD.DCD.FSD,DSD_CRS@DF_CRS,/{key}?startPeriod=2022&endPeriod=2022&format=csvfile"); p("SPLIT", key, len(d))
    except Exception as e: p("SPLITERR", key, e)
    time.sleep(3)
