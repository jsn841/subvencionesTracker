"""Traducciones al español de los códigos y etiquetas oficiales (en inglés) del CRS de la OCDE.

Solo se traduce la etiqueta; el código oficial se conserva siempre. Si aparece una
etiqueta nueva sin traducción, se muestra tal cual la publica la fuente.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "assets", "geo", "countries.json"), encoding="utf-8") as f:
    _ISO = json.load(f)

# Nombres ISO que en español se escriben de forma más habitual.
PAIS_AJUSTES = {
    "COD": "República Democrática del Congo",
    "COG": "República del Congo",
    "PRK": "Corea del Norte",
    "KOR": "Corea del Sur",
    "IRN": "Irán",
    "SYR": "Siria",
    "VEN": "Venezuela",
    "BOL": "Bolivia",
    "TZA": "Tanzania",
    "LAO": "Laos",
    "FSM": "Micronesia",
    "MDA": "Moldavia",
    "MKD": "Macedonia del Norte",
    "VNM": "Vietnam",
    "XKX": "Kosovo",
    "PSE": "Palestina",
    "CPV": "Cabo Verde",
    "SWZ": "Esuatini",
    "TUR": "Turquía",
    "CIV": "Costa de Marfil",
    "GBR": "Reino Unido",
    "USA": "Estados Unidos",
    "RUS": "Rusia",
}


def pais_es(iso3, fallback=None):
    if iso3 in PAIS_AJUSTES:
        return PAIS_AJUSTES[iso3]
    if iso3 in _ISO:
        return _ISO[iso3]["es"]
    return fallback or iso3


def iso2_a_iso3(iso2):
    for a3, v in _ISO.items():
        if v.get("a2") == iso2:
            return a3
    return None


REGIONES = {
    "South America": "Sudamérica",
    "Caribbean & Central America": "Caribe y Centroamérica",
    "South of Sahara": "África subsahariana",
    "North of Sahara": "Norte de África",
    "Middle East": "Oriente Medio",
    "South & Central Asia": "Asia meridional y central",
    "Far East Asia": "Asia oriental",
    "Europe": "Europa",
    "America": "América (varios países)",
    "Africa": "África (varios países)",
    "Asia": "Asia (varios países)",
    "Oceania": "Oceanía",
    "Regional and Unspecified": "Regional o sin especificar",
}

# Etiquetas de agrupaciones de países del CRS ("X unspecified", "X, regional"...)
_AGRUP = {
    "Developing countries": "Países en desarrollo",
    "Africa": "África",
    "Northern Africa": "Norte de África",
    "North of Sahara": "Norte de África",
    "South of Sahara": "África subsahariana",
    "Sub-Saharan Africa": "África subsahariana",
    "Western Africa": "África occidental",
    "Eastern Africa": "África oriental",
    "Middle Africa": "África central",
    "Southern Africa": "África austral",
    "America": "América",
    "South America": "Sudamérica",
    "Central America": "Centroamérica",
    "Caribbean": "Caribe",
    "Caribbean & Central America": "Caribe y Centroamérica",
    "Central America and the Caribbean": "Centroamérica y Caribe",
    "North & Central America": "Norte y Centroamérica",
    "Asia": "Asia",
    "Far East Asia": "Asia oriental",
    "Eastern Asia": "Asia oriental",
    "South Asia": "Asia meridional",
    "South & Central Asia": "Asia meridional y central",
    "Central Asia": "Asia central",
    "South-Eastern Asia": "Sudeste asiático",
    "Middle East": "Oriente Medio",
    "Oceania": "Oceanía",
    "Melanesia": "Melanesia",
    "Micronesia": "Micronesia",
    "Polynesia": "Polinesia",
    "Europe": "Europa",
    "Western Asia": "Asia occidental",
}


def agrupacion_es(label):
    """Traduce una etiqueta de agrupación del CRS. Devuelve None si no la reconoce."""
    if not label:
        return None
    l = label.strip()
    for suf, tpl in ((" unspecified", "{} (sin especificar país)"), (", regional", "{} (regional)"), (", unspecified", "{} (sin especificar país)")):
        if l.endswith(suf):
            base = l[: -len(suf)]
            if base in _AGRUP:
                return tpl.format(_AGRUP[base])
    if l in _AGRUP:
        return _AGRUP[l]
    especiales = {
        "Palestinian Authority or West Bank and Gaza Strip": "Autoridad Palestina / Cisjordania y Franja de Gaza",
        "West Bank and Gaza Strip": "Cisjordania y Franja de Gaza",
        "China (People’s Republic of)": "China",
        "China (People's Republic of)": "China",
        "Kosovo": "Kosovo",
        "Bilateral, unspecified": "Bilateral sin especificar",
        "Developing countries unspecified": "Países en desarrollo (sin especificar país)",
    }
    return especiales.get(l)


# Organismo español que informa la ayuda al CRS -> (nivel de administración, nombre en español)
AGE = "Administración General del Estado"
CCAA = "Comunidades autónomas"
EELL = "Entidades locales"
UNIV = "Universidades públicas"
OTROS = "Otros"
AGENCIAS = {
    "Spanish Agency for International Development Co-operation": (AGE, "Agencia Española de Cooperación Internacional para el Desarrollo (AECID)"),
    "Spanish Agency for International Development Cooperation": (AGE, "Agencia Española de Cooperación Internacional para el Desarrollo (AECID)"),
    "Ministry of Foreign Affairs and Co-operation": (AGE, "Ministerio de Asuntos Exteriores y de Cooperación"),
    "Ministry of Foreign Affairs and Cooperation": (AGE, "Ministerio de Asuntos Exteriores y de Cooperación"),
    "Ministry of Foreign Affairs, European Union and Co-operation": (AGE, "Ministerio de Asuntos Exteriores, Unión Europea y Cooperación"),
    "Ministry of Foreign Affairs, European Union and Cooperation": (AGE, "Ministerio de Asuntos Exteriores, Unión Europea y Cooperación"),
    "Ministry of Economy and Business": (AGE, "Ministerio de Economía y Empresa"),
    "Ministry of Economy and Finance": (AGE, "Ministerio de Economía y Hacienda"),
    "Ministry of Economy": (AGE, "Ministerio de Economía"),
    "Ministry of Economy and Competitiveness": (AGE, "Ministerio de Economía y Competitividad"),
    "Ministry of Economic Affairs and Digital Transformation": (AGE, "Ministerio de Asuntos Económicos y Transformación Digital"),
    "Ministry of Economy, Trade and Business": (AGE, "Ministerio de Economía, Comercio y Empresa"),
    "Ministry of Finance": (AGE, "Ministerio de Hacienda"),
    "Ministry of Finance and Public Administration": (AGE, "Ministerio de Hacienda y Administraciones Públicas"),
    "Ministry of Finance and Public Function": (AGE, "Ministerio de Hacienda y Función Pública"),
    "Ministry of Labour, Migration and Social Security": (AGE, "Ministerio de Trabajo, Migraciones y Seguridad Social"),
    "Ministry of Labour and Social Affairs": (AGE, "Ministerio de Trabajo y Asuntos Sociales"),
    "Ministry of Labour and Immigration": (AGE, "Ministerio de Trabajo e Inmigración"),
    "Ministry of Employment and Social Security": (AGE, "Ministerio de Empleo y Seguridad Social"),
    "Ministry of Inclusion, Social Security and Migration": (AGE, "Ministerio de Inclusión, Seguridad Social y Migraciones"),
    "Ministry of Health": (AGE, "Ministerio de Sanidad"),
    "Ministry of Health and Consumer Affairs": (AGE, "Ministerio de Sanidad y Consumo"),
    "Ministry of Health, Social Services and Equality": (AGE, "Ministerio de Sanidad, Servicios Sociales e Igualdad"),
    "Ministry of Public Works": (AGE, "Ministerio de Fomento"),
    "Ministry of Development": (AGE, "Ministerio de Fomento"),
    "Ministry of Transport, Mobility and Urban Agenda": (AGE, "Ministerio de Transportes, Movilidad y Agenda Urbana"),
    "Ministry of Interior": (AGE, "Ministerio del Interior"),
    "Ministry of the Interior": (AGE, "Ministerio del Interior"),
    "Ministry of Agriculture, Fisheries, and Food": (AGE, "Ministerio de Agricultura, Pesca y Alimentación"),
    "Ministry of Agriculture, Fisheries and Food": (AGE, "Ministerio de Agricultura, Pesca y Alimentación"),
    "Ministry of Defense": (AGE, "Ministerio de Defensa"),
    "Ministry of Defence": (AGE, "Ministerio de Defensa"),
    "Ministry of Industry and Energy": (AGE, "Ministerio de Industria y Energía"),
    "Ministry of Industry, Tourism and Trade": (AGE, "Ministerio de Industria, Turismo y Comercio"),
    "Ministry of Industry, Trade and Tourism": (AGE, "Ministerio de Industria, Comercio y Turismo"),
    "Ministry of Education, Culture and Sports": (AGE, "Ministerio de Educación, Cultura y Deporte"),
    "Ministry of Education and Science": (AGE, "Ministerio de Educación y Ciencia"),
    "Ministry of Education": (AGE, "Ministerio de Educación"),
    "Ministry of Culture": (AGE, "Ministerio de Cultura"),
    "Ministry of Culture and Sport": (AGE, "Ministerio de Cultura y Deporte"),
    "Ministry of Science and Innovation": (AGE, "Ministerio de Ciencia e Innovación"),
    "Ministry of Science, Innovation and Universities": (AGE, "Ministerio de Ciencia, Innovación y Universidades"),
    "Ministry of the Environment": (AGE, "Ministerio de Medio Ambiente"),
    "Ministry of the Environment and Rural and Marine Environs": (AGE, "Ministerio de Medio Ambiente y Medio Rural y Marino"),
    "Ministry of Agriculture, Food and Environment": (AGE, "Ministerio de Agricultura, Alimentación y Medio Ambiente"),
    "Ministry for the Ecological Transition": (AGE, "Ministerio para la Transición Ecológica"),
    "Ministry for the Ecological Transition and the Demographic Challenge": (AGE, "Ministerio para la Transición Ecológica y el Reto Demográfico"),
    "Ministry of the Presidency": (AGE, "Ministerio de la Presidencia"),
    "Ministry of Justice": (AGE, "Ministerio de Justicia"),
    "Ministry of Equality": (AGE, "Ministerio de Igualdad"),
    "Ministry of Social Rights and 2030 Agenda": (AGE, "Ministerio de Derechos Sociales y Agenda 2030"),
    "Ministry of Territorial Policy": (AGE, "Ministerio de Política Territorial"),
    "Others ministries": (AGE, "Otros ministerios"),
    "Other ministries": (AGE, "Otros ministerios"),
    "Central administration": (AGE, "Administración central"),
    "Central Administration": (AGE, "Administración central"),
    "Autonomous Governments": (CCAA, "Comunidades autónomas"),
    "Autonomous Communities": (CCAA, "Comunidades autónomas"),
    "Municipalities": (EELL, "Entidades locales"),
    "Local Governments": (EELL, "Entidades locales"),
    "Public Universities": (UNIV, "Universidades públicas"),
    "Universities": (UNIV, "Universidades públicas"),
    "Miscellaneous": (OTROS, "Varios"),
    "Other": (OTROS, "Otros"),
}


AGENCIAS.update({
    "Development Promotion Fund": (AGE, "Fondo para la Promoción del Desarrollo (FONPRODE)"),
    "Fund for the Promotion of Development": (AGE, "Fondo para la Promoción del Desarrollo (FONPRODE)"),
    "Compañía Española de Financiación del Desarrollo": (AGE, "Compañía Española de Financiación del Desarrollo (COFIDES)"),
    "Ministry of Science and Technology": (AGE, "Ministerio de Ciencia y Tecnología"),
})
_PREFIJOS = (
    (CCAA, ("comunidad", "ciudad autónoma", "ciudad autonoma", "generalitat", "junta de", "xunta", "gobierno de",
            "principado", "región de", "region de", "illes balears", "govern", "autonomous")),
    (EELL, ("ayuntamiento", "diputación", "diputacion", "cabildo", "consell", "mancomunidad", "fondo de cooperación",
            "fons", "federación", "municipal", "local", "ajuntament", "concello", "udal")),
    (UNIV, ("universidad", "universitat", "universidade", "university", "unibertsitate")),
    (AGE, ("ministry", "ministerio", "spanish", "state secretariat", "secretaría", "secretariat", "agencia",
           "instituto", "fundación internacional y para iberoamérica", "compañía española", "fondo para", "fonprode")),
)


def agencia(nombre):
    """Devuelve (nivel_administración, nombre_es) para un organismo informante del CRS."""
    if not nombre:
        return (OTROS, "No informado")
    nombre = nombre.strip()
    if nombre in AGENCIAS:
        return AGENCIAS[nombre]
    low = nombre.lower()
    for nivel, prefijos in _PREFIJOS:
        if low.startswith(prefijos):
            return (nivel, nombre)
    return (OTROS, nombre)


# Modalidad / tipo de ayuda (clasificación oficial del CAD)
MODALIDADES = {
    "A01": "Apoyo presupuestario general",
    "A02": "Apoyo presupuestario sectorial",
    "B01": "Contribución general a ONG, entidades privadas e institutos de investigación",
    "B02": "Contribución general a organismos multilaterales",
    "B021": "Contribución general a organismos multilaterales",
    "B022": "Contribución general a fondos globales",
    "B03": "Contribución a programas y fondos específicos gestionados por socios",
    "B031": "Contribución a fondos de varios donantes y varias entidades",
    "B032": "Contribución a fondos de varios donantes y una entidad",
    "B033": "Contribución a fondos de un solo donante",
    "B04": "Fondos comunes (cesta de donantes)",
    "C01": "Proyecto",
    "D01": "Personal del país donante",
    "D02": "Otra asistencia técnica",
    "E01": "Becas y formación en el país donante",
    "E02": "Costes imputados de estudiantes",
    "F01": "Alivio de la deuda",
    "G01": "Costes administrativos no incluidos en otras partidas",
    "H01": "Sensibilización sobre el desarrollo (en España)",
    "H02": "Refugiados y solicitantes de asilo en el país donante",
    "H03": "Solicitantes de asilo finalmente aceptados (en el país donante)",
    "H04": "Solicitantes de asilo finalmente rechazados (en el país donante)",
    "H05": "Refugiados reconocidos (en el país donante)",
    "H06": "Refugiados y solicitantes de asilo en otros países proveedores",
    "0": "No aplicable / no informado",
    "_Z": "No aplicable / no informado",
}

CANALES = {
    "10000": "Sector público",
    "11000": "Sector público del país donante",
    "12000": "Sector público del país receptor",
    "13000": "Sector público de terceros países",
    "20000": "ONG y sociedad civil",
    "21000": "ONG internacionales",
    "22000": "ONG del país donante",
    "23000": "ONG de países en desarrollo",
    "30000": "Alianzas público-privadas",
    "40000": "Organismos multilaterales",
    "41000": "Naciones Unidas",
    "42000": "Instituciones de la Unión Europea",
    "43000": "Fondo Monetario Internacional",
    "44000": "Grupo Banco Mundial",
    "45000": "Organización Mundial del Comercio",
    "46000": "Bancos regionales de desarrollo",
    "47000": "Otras organizaciones multilaterales",
    "50000": "Universidades e institutos de investigación",
    "51000": "Universidades e institutos de investigación",
    "60000": "Sector privado",
    "61000": "Sector privado del país donante",
    "62000": "Sector privado del país receptor",
    "63000": "Sector privado de terceros países",
    "90000": "Otros",
    "0": "No informado",
}

CANAL_NOMBRE = {
    "Donor Government": "Gobierno donante (España)",
    "Recipient Government": "Gobierno receptor",
    "Central Government": "Gobierno central (receptor)",
    "Local Government": "Gobierno local (receptor)",
    "Public sector institutions": "Instituciones del sector público",
    "Donor country-based NGO": "ONG del país donante (España)",
    "International NGO": "ONG internacional",
    "Developing country-based NGO": "ONG del país en desarrollo",
    "Other public entities in donor country": "Otras entidades públicas del país donante",
    "Other public entities in recipient country": "Otras entidades públicas del país receptor",
    "University, college or other teaching institution, research institute or think-tank": "Universidad, centro de enseñanza o de investigación",
    "Private sector in provider country": "Sector privado del país donante",
    "Private sector in recipient country": "Sector privado del país receptor",
    "Other": "Otros",
}

SECTORES = {
    "111": "Educación (nivel sin especificar)", "112": "Educación básica", "113": "Educación secundaria",
    "114": "Educación postsecundaria", "121": "Salud general", "122": "Salud básica",
    "123": "Enfermedades no transmisibles", "130": "Población y salud reproductiva",
    "140": "Agua y saneamiento", "151": "Gobierno y sociedad civil", "152": "Conflictos, paz y seguridad",
    "160": "Otros servicios sociales", "210": "Transporte y almacenamiento", "220": "Comunicaciones",
    "231": "Energía: política", "232": "Energía renovable", "233": "Energía no renovable",
    "234": "Energía híbrida", "235": "Energía nuclear", "236": "Distribución de energía",
    "240": "Banca y servicios financieros", "250": "Empresas y otros servicios", "311": "Agricultura",
    "312": "Silvicultura", "313": "Pesca", "321": "Industria", "322": "Minería", "323": "Construcción",
    "331": "Comercio", "332": "Turismo", "410": "Protección del medio ambiente", "430": "Multisectorial",
    "510": "Apoyo presupuestario general", "520": "Ayuda alimentaria para el desarrollo",
    "530": "Otra ayuda en productos", "600": "Acciones relacionadas con la deuda",
    "720": "Ayuda de emergencia", "730": "Reconstrucción y rehabilitación", "740": "Prevención de desastres",
    "910": "Costes administrativos", "930": "Refugiados en el país donante", "998": "Sin asignar / sin especificar",
}


def sector_es(code, label=None):
    code = str(code or "")
    if len(code) >= 3 and code[:3] in SECTORES:
        return SECTORES[code[:3]]
    return label or "Sin especificar"


def instrumento_crs(finance_code, modality_code, measure_code):
    """Instrumento financiero a partir del tipo de financiación del CRS."""
    try:
        fc = int(float(finance_code))
    except (TypeError, ValueError):
        fc = None
    if modality_code == "F01" or (fc is not None and 600 <= fc < 1000):
        return "Alivio de la deuda"
    if fc is None:
        return {"11": "Donación", "13": "Préstamo", "19": "Participación en capital"}.get(str(measure_code), "Otros")
    if fc < 300:
        return "Donación"
    if fc < 400:
        return "Depósito"
    if fc < 500:
        return "Préstamo"
    if fc < 600:
        return "Participación en capital"
    if fc >= 1100:
        return "Garantía"
    return "Otros"


CATEGORIAS = {
    "10": "Ayuda Oficial al Desarrollo (AOD)",
    "21": "Otros flujos oficiales",
    "22": "Otros flujos oficiales",
    "30": "Flujos privados",
    "ODA": "Ayuda Oficial al Desarrollo (AOD)",
    "Non-export credit OOF": "Otros flujos oficiales",
}
