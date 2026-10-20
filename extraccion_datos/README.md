# Módulo de Extracción y Curaduría de Datos Externos Reales

Este directorio contiene el código, cuaderno reproducible y documentación detallada sobre la adquisición de variables agroclimáticas y edáficas públicas reales para el **Reto AgroCebada FIRA 2026**.

---

## 1. Principio Fundamental: Cero Variables Simuladas
En estricto apego a las bases del concurso y a las mejores prácticas de la ciencia de datos, **el 100 % de los datos utilizados proviene de observaciones y reanálisis físicos reales**. No se generaron variables sintéticas, simuladas ni pseudo-aleatorias.

---

## 2. Fuentes de Información Consultadas

| Fuente | Entidad Proveedora | Resolución Espacial / Temporal | Variables Adquiridas | Justificación Agronómica |
|---|---|---|---|---|
| **ECMWF ERA5 / ERA5-Land** | Open-Meteo Historical Weather API | ~0.1° (~10 km) / Diaria (2022–2025) | Temperatura máx/mín/media, precipitación, evapotranspiración $ET_0$ FAO-56 Penman-Monteith, radiación solar, rachas secas, GDD | Los rasters oficiales son mensuales; la cebada de secano requiere resolución diaria para capturar heladas tardías, olas de calor y rachas secas críticas en floración. |
| **ISRIC SoilGrids 2.0** | World Soil Information (ISRIC) | 250 m / Perfil multicapa (0–60 cm) | % Arcilla, % arena, % limo, pH en agua, carbono orgánico del suelo (SOC), nitrógeno total, CEC, densidad aparente | La retención hídrica en temporal depende fuertemente de la textura y profundidad del suelo, información ausente en el dataset original. |
| **INEGI CEM 4.0** | Instituto Nacional de Estadística y Geografía | 120 m / Raster continuo | Elevación zonal, pendiente en grados, orientación de ladera (aspecto Horn 3x3), índice TPI (1 y 3 km) | Modela la redistribución orográfica del agua y la acumulación de aire frío en fondos de valle. |

---

## 3. Contenido del Directorio

* **`Extraccion_Datos_Externos_Reales.ipynb`**: Cuaderno interactivo completamente documentado y ejecutado, que guía paso a paso la consulta a las APIs, la limpieza espacial y la derivación biofísica de variables con visualizaciones diagnósticas.
* **`fetch_external.py`**: Script de extracción en Python con manejo robusto de excepciones, reintentos exponenciales y caché local para reproducibilidad offline.

---

## 4. Instrucciones de Reproducción

Para volver a ejecutar la extracción desde cero o actualizar las variables:
```bash
python -c "import fetch_external as fx; fx.fetch_openmeteo(fx.centroides()); fx.fetch_soilgrids(fx.centroides())"
```
O simplemente abrir `Extraccion_Datos_Externos_Reales.ipynb` en Jupyter Lab / VSCode y ejecutar las celdas secuencialmente.
