"""Diagnóstico: beneficiarios con identificador enmascarado en la BDNS (selección exterior).
No imprime nombres de posibles personas físicas: solo recuentos y ejemplos de los que contienen
palabras de organización (entidades)."""
import collections, json, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, "scripts")
import fetch_bdns as F
ORG = re.compile(r"\b(ASOC|ASSOC|FUNDA|FOUND|STIFT|STICHT|S\.?L\.?U?|S\.?A\.?|SOCIEDAD|SOCIET|COOP|UNIVERS|INSTIT|CENTRO|CENTRE|CENTER|COLEGIO|COL·LEGI|COLLEGE|SCHOOL|ESCUELA|ACADEM|ONG|NGO|CONGREGA|HERMAN|MISION|MISSION|AYUNTAM|MUNICIP|GOBIERNO|GOVERN|MINIST|CLUB|FEDERA|CONFEDER|COMIT|CONSE|ORGANI[SZ]A|CORPORA|EMPRESA|LTD|LIMITED|INC|GMBH|S\.?R\.?L|SARL|SAS|ASBL|VZW|E\.?V\.?|ONLUS|HOSPITAL|IGLESIA|PARROQ|OBISPAD|DIOCES|ARZOBISP|CARITAS|CRUZ ROJA|MOVIMIENTO|PLATAFORMA|COORDINADORA|UNION|UNIÓN|ALIANZA|ALLIANCE|COMUNIDAD|TRUST|RED |NETWORK|ASOCIATIA|AGENCIA|AGENCY|OFICINA|OFFICE|PROGRAM|FONDO|FUND|BANCO|BANK|CONSORCIO|CONSORTIUM|ORDEN|ORDER|SINDICATO|PARTIDO|ESTADO|REPUBLIC|NACIONES UNIDAS|UNITED NATIONS|INTERNATIONAL|INTERNACIONAL|NATIONAL|NACIONAL|ASAMBLEA|COMMISSION|COMISION|COMISIÓN|SERVICIO|SERVICE|PROYECTO|PROJECT|GRUPO|GROUP|CAMARA|CÁMARA|MUSEO|MUSEUM|BIBLIOTECA|LIBRARY|ARCHIVO|TEATRO|THEATRE|EDITORIAL|EDICIONES|EDITIONS|PUBLISH|VERLAG|PRESS)", re.I)
pat = collections.Counter(); org_masked = collections.Counter(); ejemplos = []
total = 0
regs = F.regiones_exteriores()
lotes = [{"regiones": rid} for rid, cod, nom in regs] + [{"finalidad": F.FINALIDAD_COOPERACION}]
vistos = set()
for q in lotes:
    for c in F.concesiones(q):
        if c["id"] in vistos: continue
        vistos.add(c["id"]); total += 1
        ident, nombre, persona = F.separar_beneficiario(c.get("beneficiario"))
        if not persona: continue
        forma = re.sub(r"\d", "9", ident)
        es_org = bool(ORG.search(nombre))
        pat[(forma, es_org)] += 1
        if es_org:
            org_masked[c.get("nivel2")] += 1
            if len(ejemplos) < 60: ejemplos.append((forma, nombre[:80], c.get("convocatoria", "")[:60]))
    time.sleep(2)
print("TOTAL concesiones", total)
print("ENMASCARADAS por forma del identificador y si el nombre parece entidad:")
for (forma, es_org), n in sorted(pat.items(), key=lambda x: -x[1]): print(f"  {forma:15s} entidad={es_org!s:5s} {n}")
print("ENTIDADES con identificador enmascarado, por organismo:", org_masked.most_common(15))
print("EJEMPLOS (solo nombres con palabras de organización):")
for e in ejemplos: print("  ", e)
