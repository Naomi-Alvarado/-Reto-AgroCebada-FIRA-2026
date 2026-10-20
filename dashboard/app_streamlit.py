"""
app_streamlit.py
Plataforma Interactiva AgroCebada Intelligence (Versión Streamlit)
Diseñada para agrónomos, productores y analistas de crédito FIRA.
Permite la consulta ágil de rendimientos estimados, intervalos de confianza y simulación de escenarios.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

try:
    import streamlit as st
except ImportError:
    st = None

if st is not None:
    # Configuración de página
    st.set_page_config(
        page_title="AgroCebada Intelligence | FIRA 2026",
        page_icon="🌾",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Estilos CSS modernos
    st.markdown("""
        <style>
        .main { background-color: #0b0f19; color: #f8fafc; }
        .stMetric { background-color: rgba(16, 23, 38, 0.75); padding: 15px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.08); }
        .stButton>button { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; font-weight: 600; border-radius: 8px; border: none; }
        </style>
    """, unsafe_allow_html=True)

    # Cargar datos
    BASE_DIR = Path(__file__).resolve().parent
    DATA_PATH = BASE_DIR / "data" / "parcels_db.json"
    if not DATA_PATH.exists():
        DATA_PATH = BASE_DIR.parent / "dashboard" / "data" / "parcels_db.json"

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        parcels_data = json.load(f)

    df_parcels = pd.DataFrame(parcels_data)
    parcel_map = {p["id"]: p for p in parcels_data}

    # Barra lateral
    st.sidebar.image("https://img.icons8.com/color/96/barley.png", width=64)
    st.sidebar.title("AgroCebada FIRA 2026")
    st.sidebar.markdown("**Herramienta de Consulta y Decisión Agronómica / Financiera**")
    st.sidebar.markdown("---")

    filtro_conjunto = st.sidebar.selectbox("Conjunto de Datos:", ["Todos", "Evaluación Oficial FIRA (59)", "Entrenamiento (138)"])
    filtro_muni = st.sidebar.selectbox("Municipio:", ["Todos"] + sorted(list(df_parcels["municipio"].unique())))

    # Filtrar parcelas
    parcels_filtradas = [
        p for p in parcels_data
        if (filtro_conjunto == "Todos" or (filtro_conjunto.startswith("Evaluación") and p["conjunto"] == "PREDICCION") or (filtro_conjunto.startswith("Entrenamiento") and p["conjunto"] == "ENTRENAMIENTO"))
        and (filtro_muni == "Todos" or p["municipio"] == filtro_muni)
    ]

    if not parcels_filtradas:
        st.warning("No hay parcelas con los filtros seleccionados.")
        st.stop()

    parcel_options = [f"{p['id']} — {p['municipio']} ({p['conjunto']})" for p in parcels_filtradas]
    selected_option = st.sidebar.selectbox("Seleccione Parcela:", parcel_options)
    selected_id = selected_option.split(" — ")[0]
    p = parcel_map[selected_id]

    # Encabezado principal
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.title(f"🌾 Parcela {p['id']} — {p['municipio']}, {p['estado']}")
        st.markdown(f"**Conjunto:** `{p['conjunto']}` | **Superficie:** `{p['area_ha']} ha` | **Coordenadas:** `{p['lat']}° N, {p['lon']}° W`")
    with col_t2:
        st.markdown("<br>", unsafe_allow_html=True)
        csv_data = pd.DataFrame([{
            "ID_POLIGONO": p["id"],
            "RENDIMIENTO_T_HA": p["rendimiento_pred"] or p["rendimiento_real"]
        }]).to_csv(index=False)
        st.download_button("Descargar Predicción (.csv)", csv_data, f"prediccion_{p['id']}.csv", "text/csv")

    st.markdown("---")

    # Fila de métricas clave
    yield_val = p["rendimiento_pred"] if p["rendimiento_pred"] is not None else p["rendimiento_real"]
    ic_inf = p["ic90_inf"] if p["ic90_inf"] is not None else round(max(0.0, yield_val - 0.746), 4)
    ic_sup = p["ic90_sup"] if p["ic90_sup"] is not None else round(yield_val + 0.746, 4)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rendimiento Estimado", f"{yield_val:.4f} t/ha", delta=f"{p['finance']['margen_t_ha']:+.2f} t/ha vs costo")
    m2.metric("Intervalo de Incertidumbre (90%)", f"± 0.75 t/ha", help=f"Rango fisiológico: [{ic_inf:.2f} — {ic_sup:.2f}] t/ha")
    m3.metric("Riesgo Crediticio FIRA", p["finance"]["riesgo"].split("(")[0].strip())
    m4.metric("Margen Neto Esperado", f"${p['finance']['margen_mxn_ha']:,.0f} MXN/ha")

    st.markdown("---")

    # Pestañas de detalle
    tab_bio, tab_sim, tab_fira = st.tabs(["📊 Perfil Biofísico & Fenológico", "🎛️ Simulador 'What-If'", "🏦 Inclusión Financiera & Crédito"])

    with tab_bio:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("Curva Estacional de Vigor (NDVI)")
            pheno = p["phenology"]
            df_pheno = pd.DataFrame({
                "Etapa Fenológica": ["1. Emergencia (Jun)", "2. Vegetativo (Jul)", "3. Espigamiento (Ago)", "4. Llenado (Sep)", "5. Madurez (Oct)"],
                "NDVI Planet (3m)": [pheno["est"], pheno["veg"], pheno["head"], pheno["fill"], pheno["mat"]]
            })
            st.line_chart(df_pheno.set_index("Etapa Fenológica"))
            st.caption("Evolución del dosel fotosintéticamente activo durante el ciclo primavera-verano 2025.")

        with c2:
            st.subheader("Condicionantes de Suelo y Clima")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.write(f"🏔️ **Altitud Zonal:** {p['elev_m']} m s.n.m.")
                st.write(f"📐 **Pendiente Media:** {p['slope_deg']}°")
                st.write(f"🧱 **Arcilla (0-30 cm):** {p['soil']['clay_pct']} %")
                st.write(f"🧪 **pH del Suelo:** {p['soil']['ph']}")
            with col_s2:
                st.write(f"🌧️ **Lluvia Total Ciclo:** {p['climate']['prec_total_mm']} mm")
                st.write(f"💧 **Balance Hídrico:** {p['climate']['water_balance_mm']} mm")
                st.write(f"☀️ **Racha Seca Floración:** {p['climate']['dry_spell_days']} días")
                st.write(f"🌱 **Materia Orgánica (SOC):** {p['soil']['soc_g_kg']} g/kg")

    with tab_sim:
        st.subheader("Simulación Interactiva de Escenarios Agroclimáticos")
        st.write("Ajuste los parámetros para proyectar el impacto en el rendimiento y la viabilidad del crédito:")

        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1:
            sim_rain = st.slider("Variación en Precipitación (%):", -40, 40, 0, step=5)
        with s_col2:
            sim_dry = st.slider("Días Secos Adicionales en Floración:", 0, 20, 0, step=1)
        with s_col3:
            sim_ndvi = st.slider("Anomalía de Vigor NDVI:", -0.20, 0.20, 0.0, step=0.02)

        impact_r = 0.0075 * sim_rain
        impact_d = -0.052 * sim_dry
        impact_n = 2.80 * sim_ndvi
        sim_yield = round(max(1.2, min(6.5, yield_val + impact_r + impact_d + impact_n)), 4)
        delta_y = round(sim_yield - yield_val, 4)

        st.info(f"**Rendimiento Proyectado:** `{sim_yield:.4f} t/ha` (Variación neta: `{delta_y:+.4f} t/ha`) | **Nuevo Margen:** `${(sim_yield - 2.8)*6200:,.0f} MXN/ha`")

    with tab_fira:
        st.subheader("Dictamen de Riesgo Crediticio e Inclusión Financiera")
        fin = p["finance"]
        st.success(f"**Calificación de Riesgo:** {fin['riesgo']}")
        st.write(f"📋 **Recomendación para Intermediarios Financieros:** {fin['credito_recom']}")
        st.write(f"🛡️ **Mecanismo de Cobertura / Seguro Paramétrico:** {fin['seguro_status']}")
        st.write(f"💰 **Margen Operativo sobre Costo de Equilibrio (2.8 t/ha):** +{fin['margen_t_ha']} t/ha (~${fin['margen_mxn_ha']:,.0f} MXN/ha)")
else:
    print("Streamlit no se encuentra instalado en este entorno de consola. El archivo app_streamlit.py está listo para ser ejecutado con 'streamlit run app_streamlit.py'.")
