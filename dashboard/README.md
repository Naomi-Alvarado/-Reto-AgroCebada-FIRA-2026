# Plataforma Analítica & Dashboard AgroCebada Intelligence

Este directorio alberga la implementación práctica de la solución tecnológica (30 % de la evaluación del **Reto AgroCebada FIRA 2026**).

---

## 1. Despliegue en GitHub Pages y Modo Offline (Sin Servidor)

Para máxima accesibilidad por parte de evaluadores, productores y jurado, la plataforma está empaquetada en un **único archivo autónomo** que funciona tanto en la web como en local:

* **En GitHub Pages:** El archivo se encuentra en `docs/index.html`. Al activar GitHub Pages en el repositorio apuntando a la carpeta `/docs`, la plataforma queda inmediatamente en línea.
* **Modo Offline:** Haga doble clic sobre `index.html` (o `dashboard_offline.html`) para abrirlo en cualquier navegador (Chrome, Edge, Firefox, Safari) **sin necesidad de instalar Python, librerías ni iniciar servidores**.

---

## 2. Alternativa con Streamlit (`app_streamlit.py`)

Para entornos analíticos de Python interactivo:
```bash
pip install streamlit
streamlit run app_streamlit.py
```
Permite explorar los rendimientos por parcela, consultar los intervalos de confianza conformales y ejecutar simulaciones dinámicas *What-If*.

---

## 3. Alternativa con Servidor Flask (`app_flask.py`)

Para despliegues en servidores locales o contenedores Docker con API REST:
```bash
pip install flask
python app_flask.py
```
Disponible inmediatamente en `http://127.0.0.1:5000` con endpoints JSON `/api/parcels`, `/api/parcel/<id>` y `/api/simulate`.

---

## 4. Funcionalidades Orientadas a la Toma de Decisiones

1. **Mapa Interactivo Vectorial:** Visualización de las 197 parcelas con polígonos coloreados por nivel de rendimiento y filtros por municipio.
2. **Estimación Conformal:** Rendimiento en t/ha a 4 decimales con radio de incertidumbre formal ($\pm 0.7460$ t/ha al 90 % de confianza).
3. **Curva Fenológica:** Perfil temporal de vigor foliar (NDVI) a lo largo de las 5 fases de desarrollo.
4. **Scoring Crediticio FIRA:** Clasificación de riesgo de crédito (Grados A, B, C), margen esperado en pesos por hectárea y elegibilidad para apoyos de aseguramiento paramétrico.
5. **Simulador de Sensibilidad Agroclimática:** Proyección de cambios en el rendimiento ante escenarios de sequía, exceso de lluvia o estrés de dosel.
