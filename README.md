# Ayudas de España al exterior

Web pública y gratuita que muestra las ayudas y subvenciones que las administraciones públicas españolas conceden a entidades, gobiernos o proyectos en otros países. Usa solo datos oficiales y los muestra tal como los publican las fuentes.

- **Web:** https://jsn841.github.io/subvencionesTracker/ (cuando GitHub Pages esté activado)
- **Metodología:** [metodologia.html](metodologia.html)

## Fuentes

| Capa | Fuente | Periodo | Actualización |
|---|---|---|---|
| Ayuda al desarrollo | OCDE, Creditor Reporting System (API SDMX) | 1995 – último año publicado | cada lunes |
| Concesiones | BDNS / infosubvenciones.es (API pública) | desde 2022, acumulativo | cada día |
| Actividades AECID | Registro IATI (AECID) | años recientes | cada día |

Las capas no se suman entre sí, porque una misma ayuda puede aparecer en varias fuentes. Los detalles están en la página de metodología.

## Cómo funciona

```
scripts/            programas en Python (solo biblioteca estándar) que descargan y preparan los datos
  fetch_crs.py      OCDE (CRS) → data/aod/AAAA.json
  fetch_bdns.py     BDNS       → data/bdns/AAAA.json (nunca borra: acumula)
  fetch_iati.py     IATI AECID → data/iati/AAAA.json
  build_manifest.py resumen de todo → data/manifest.json
data/               los datos, un archivo pequeño por año y fuente
index.html          la web (filtros, gráficas, mapa, fichas, descargas)
metodologia.html    explicación de fuentes y limitaciones
assets/             estilos, código de la web y librerías (ECharts, SheetJS, mapa)
.github/workflows/  tareas automáticas de GitHub Actions
```

### Tareas automáticas (pestaña «Actions» de GitHub)

- **Carga histórica**: se lanza a mano una vez y descarga todo el historial (tarda en torno a una hora).
- **Actualización diaria**: se ejecuta sola cada día a las 05:17 UTC; añade las concesiones nuevas y comprueba si hay datos nuevos de la OCDE (los lunes) y de AECID.
- **Publicar web**: publica la web en GitHub Pages cada vez que cambian el código o los datos.

### Probar en tu ordenador (opcional)

```
python scripts/fetch_iati.py
python scripts/fetch_crs.py --years 2023-2023
python scripts/fetch_bdns.py
python scripts/build_manifest.py
python -m http.server 8000      # y abre http://localhost:8000
```

## Licencias

Código: MIT. Los datos pertenecen a sus fuentes (OCDE, IGAE, AECID) y se reutilizan según sus condiciones, enlazadas en la página de metodología.
