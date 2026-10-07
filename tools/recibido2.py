import json, sys, urllib.request, urllib.parse, csv, io, re, collections, time
UA = {"User-Agent": "Mozilla/5.0 subvencionesTracker-analisis"}
def get(url, timeout=600):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r: return r.read()
def p(*a): print(*a, flush=True)
part = sys.argv[1]
if part == "dportal":
    base = "https://d-portal.org/q.json?"
    tries = [
        "from=act,country&country_code=ES&limit=5",
        "from=act,country&country_code=ES&select=reporting_ref,count&groupby=reporting_ref&limit=-1",
        "from=act,country&country_code=ES&select=reporting,reporting_ref,count_aid,sum_of_percent_of_spend,sum_of_percent_of_commitment&groupby=reporting_ref&limit=-1",
    ]
    for q in tries:
        try: s = get(base + q).decode(); p("OK", q, len(s)); p(s[:3000])
        except Exception as e: p("ERR", q, e)
    try:
        s = get(base + "from=act,country&country_code=ES&limit=-1")
        j = json.loads(s); rows = j.get("rows", j)
        p("NACT", len(rows)); p("KEYS", list(rows[0].keys()) if rows else None)
        json.dump(rows, open("out/dportal_es.json", "w"))
    except Exception as e: p("ERR all", e)
elif part == "bde":
    for t in ["be1701", "be1702", "be1703", "be1704", "be1705", "be1706", "be1707", "be1708"]:
        for u in [f"https://www.bde.es/webbe/es/estadisticas/compartido/datos/csv/{t}.csv", f"https://www.bde.es/webbde/es/estadis/infoest/series/{t}.csv"]:
            try:
                b = get(u); s = b.decode("latin-1")
                p("OK", u, len(s)); open(f"out/{t}.csv", "w").write(s)
                lines = s.splitlines()
                for i, l in enumerate(lines[:8]): p("  L", i, l[:600])
                break
            except Exception as e: p("ERR", u, str(e)[:80])
