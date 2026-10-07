"""Análisis puntual: ayuda que España ha RECIBIDO de otros países (no UE)."""
import csv, io, json, re, sys, urllib.request, urllib.parse, collections, gzip, time
UA = {"User-Agent": "Mozilla/5.0 subvencionesTracker-analisis"}
def get(url, headers=None, timeout=900):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = r.read()
        return gzip.decompress(b) if r.headers.get("Content-Encoding") == "gzip" else b
def p(*a): print(*a, flush=True)
part = sys.argv[1]
if part == "dac2a2":
    H = {"Accept": "application/vnd.sdmx.structure+json;version=1.0"}
    for space in ["public", "dcd-public"]:
        for flow in ["DSD_DAC2@DF_DAC2A", "DSD_DAC1@DF_DAC1"]:
            try:
                st = json.loads(get(f"https://sdmx.oecd.org/{space}/rest/dataflow/OECD.DCD.FSD/{flow}/latest?references=all", headers=H))
                d = st["data"]
                dims = [x["id"] for x in d["dataStructures"][0]["dataStructureComponents"]["dimensionList"]["dimensions"]]
                p("FLOW", space, flow, dims)
                for cl in d.get("codelists", []):
                    hits = [(c["id"], c.get("name")) for c in cl["codes"] if "Spain" in str(c.get("name")) or c["id"] in ("ESP", "1", "50")]
                    if hits: p("  CL", cl["id"], hits[:10])
            except Exception as e: p("ERR", space, flow, str(e)[:150])
    for space in ["public", "dcd-public"]:
        for key in [".ESP...", "..ESP..", ".ESP....", "ESP...."]:
            u = f"https://sdmx.oecd.org/{space}/rest/data/OECD.DCD.FSD,DSD_DAC2@DF_DAC2A,/{key}?format=csvfilewithlabels"
            try:
                txt = get(u).decode("utf-8-sig"); p("OK", u, len(txt))
                open(f"out/dac2a_{space}.csv", "w").write(txt)
                rows = list(csv.DictReader(io.StringIO(txt)))
                for k in rows[0]:
                    if len(set(r[k] for r in rows)) < 60: p("V", k, collections.Counter(r[k] for r in rows).most_common(60))
                p("YEARS", sorted(set(r["TIME_PERIOD"] for r in rows))); break
            except Exception as e: p("ERR", u, str(e)[:100])
            time.sleep(3)
elif part == "dac2a":
    # 1) estructura DAC2A
    for flow in ["DSD_DAC2@DF_DAC2A"]:
        st = json.loads(get(f"https://sdmx.oecd.org/public/rest/dataflow/OECD.DCD.FSD/{flow}/latest?references=datastructure",
                            headers={"Accept": "application/vnd.sdmx.structure+json;version=1.0"}))
        dims = [d["id"] for d in st["data"]["dataStructures"][0]["dataStructureComponents"]["dimensionList"]["dimensions"]]
        p("DIMS", dims)
        key = ".".join("ESP" if d == "RECIPIENT" else "" for d in dims)
        u = f"https://sdmx.oecd.org/public/rest/data/OECD.DCD.FSD,{flow},/{key}?format=csvfilewithlabels"
        p("URL", u)
        txt = get(u).decode("utf-8-sig")
        open(f"out/{flow.replace('@','_')}_ESP.csv", "w").write(txt)
        rows = list(csv.DictReader(io.StringIO(txt)))
        p("ROWS", len(rows), list(rows[0].keys()))
        for k in rows[0]:
            if k[0].isupper() and len(set(r[k] for r in rows)) < 80:
                p("V", k, collections.Counter(r[k] for r in rows).most_common(60))
        p("YEARS", sorted(set(r["TIME_PERIOD"] for r in rows)))
elif part == "crs":
    # CRS con España como receptora
    st = json.loads(get("https://sdmx.oecd.org/dcd-public/rest/availableconstraint/OECD.DCD.FSD,DSD_CRS@DF_CRS,/.ESP........./all/TIME_PERIOD",
                        headers={"Accept": "application/vnd.sdmx.structure+json;version=1.0"}))
    p("AVAIL", json.dumps(st)[:800])
elif part == "greenbook":
    urls = []
    try:
        j = json.loads(get("https://catalog.data.gov/api/3/action/package_search?q=greenbook&rows=10"))
    except Exception as e:
        p("CATALOG ERR", e); j = {"result": {"results": []}}
    for pk in j["result"]["results"]:
        p("PKG", pk["title"])
        for r in pk.get("resources", []):
            p("  RES", r.get("format"), r.get("url"))
            urls.append(r.get("url"))
    try:
        h = get("https://foreignassistance.andrewheiss.com/greenbook.html").decode("utf-8", "replace")
        for l in sorted(set(re.findall(r'href="([^"]+\.(?:csv|zip|parquet|rds|xlsx)[^"]*)"', h))): p("  HEISS", l); urls.append(l if l.startswith("http") else "https://foreignassistance.andrewheiss.com/" + l)
    except Exception as e: p("HEISS ERR", e)
    for u in ["https://s3.amazonaws.com/files.explorer.devtechlab.com/us_foreign_aid_greenbook.csv",
              "https://s3.amazonaws.com/files.explorer.devtechlab.com/us_foreign_aid_country.csv",
              "https://s3.amazonaws.com/files.explorer.devtechlab.com/us_foreign_aid_complete.csv"]:
        urls.insert(0, u)
    done = False
    for u in urls:
        if not u or not re.search(r"\.csv", u, re.I): continue
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=900) as r:
                p("TRY", u, r.headers.get("content-length"))
                f = io.TextIOWrapper(r, encoding="utf-8", errors="replace")
                rd = csv.reader(f); head = next(rd); p("HEAD", head)
                ci = [i for i, h in enumerate(head) if re.search(r"country.?name|country$", h, re.I)]
                if not ci: continue
                rows = [row for row in rd if any(row[i].strip().lower() == "spain" for i in ci if i < len(row))]
                p("SPAIN ROWS", len(rows))
                with open("out/greenbook_spain.csv", "w", newline="") as o:
                    w = csv.writer(o); w.writerow(head); w.writerows(rows)
                for row in rows[:5]: p("ROW", row)
                done = True; break
        except Exception as e: p("ERR", u, str(e)[:200])
    p("DONE", done)
elif part == "eeapdf":
    import subprocess
    for u in ["https://eeagrants.org/sites/default/files/resources/EEA%20and%20Norway%20Grants%202009-2014%20-%20Spain%20Factsheet.pdf",
              "https://www.regjeringen.no/en/topics/european-policy/norwaygrants/which-countries-benefit/id685572"]:
        try:
            b = get(u)
            if b[:4] == b"%PDF":
                open("/tmp/f.pdf", "wb").write(b); subprocess.run(["pdftotext", "-layout", "/tmp/f.pdf", "/tmp/f.txt"]); p("PDF", u); p(open("/tmp/f.txt").read()[:5000])
            else:
                t = re.sub(r"\s+", " ", re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", b.decode("utf-8", "replace"), flags=re.S))
                i = t.find("Spain"); p("PAGE", u); p(t[max(0, i-2500):i+2500])
        except Exception as e: p("ERR", u, e)
elif part == "eea":
    for u in ["https://data.eeagrants.org/api/periods", "https://data.eeagrants.org/api/v1/beneficiaries",
              "https://eeagrants.org/countries/spain", "https://data.eeagrants.org/data"]:
        try: s = get(u).decode("utf-8", "replace"); p("OK", u, len(s), re.sub(r"\s+", " ", re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", s, flags=re.S))[:1500])
        except Exception as e: p("ERR", u, str(e)[:150])
