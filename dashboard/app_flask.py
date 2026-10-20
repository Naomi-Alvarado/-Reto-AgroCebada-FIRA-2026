"""
Reto AgroCebada FIRA 2026 - Servidor de Aplicación Web y Dashboard Interactivo
Plataforma analítica para la estimación de rendimiento de cebada maltera en temporal,
evaluación de riesgo crediticio e inclusión financiera agropecuaria.
"""

import os
import json
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_file

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
DATA_DIR = APP_DIR / "data"

app = Flask(__name__, template_folder=str(APP_DIR / "templates"), static_folder=str(APP_DIR / "static"))

# Cargar base de datos precomputada
with open(DATA_DIR / "parcels_db.json", "r", encoding="utf-8") as f:
    PARCELS_DB = json.load(f)

with open(DATA_DIR / "model_stats.json", "r", encoding="utf-8") as f:
    MODEL_STATS = json.load(f)

PARCEL_MAP = {p["id"]: p for p in PARCELS_DB}


@app.route("/")
def index():
    """Ruta principal: Renderiza la interfaz interactiva."""
    return render_template("index.html")


@app.route("/api/parcels", methods=["GET"])
def get_parcels():
    """Retorna la lista resumida de todas las 197 parcelas para el mapa y la tabla."""
    conjunto_filter = request.args.get("conjunto", "TODOS").upper()
    municipio_filter = request.args.get("municipio", "TODOS")

    results = []
    for p in PARCELS_DB:
        if conjunto_filter != "TODOS" and p["conjunto"] != conjunto_filter:
            continue
        if municipio_filter != "TODOS" and p["municipio"] != municipio_filter:
            continue

        results.append({
            "id": p["id"],
            "area_ha": p["area_ha"],
            "municipio": p["municipio"],
            "estado": p["estado"],
            "conjunto": p["conjunto"],
            "lat": p["lat"],
            "lon": p["lon"],
            "polygon": p["polygon"],
            "rendimiento_real": p["rendimiento_real"],
            "rendimiento_pred": p["rendimiento_pred"],
            "ic90_inf": p["ic90_inf"],
            "ic90_sup": p["ic90_sup"],
            "elev_m": p["elev_m"],
            "riesgo": p["finance"]["riesgo"],
            "color_riesgo": p["finance"]["color_riesgo"]
        })

    return jsonify({"total": len(results), "parcels": results})


@app.route("/api/parcel/<parcel_id>", methods=["GET"])
def get_parcel(parcel_id):
    """Retorna el detalle completo de una parcela por su identificador."""
    parcel = PARCEL_MAP.get(parcel_id)
    if not parcel:
        return jsonify({"error": f"Parcela {parcel_id} no encontrada"}), 404
    return jsonify(parcel)


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Retorna el benchmark de modelos, análisis SHAP y respuestas oficiales a preguntas guía."""
    return jsonify(MODEL_STATS)


@app.route("/api/simulate", methods=["POST"])
def simulate():
    """
    Simulador de escenarios 'What-If':
    Permite proyectar el impacto de variaciones agroclimáticas o de manejo sobre el rendimiento y crédito.
    """
    data = request.get_json() or {}
    pid = data.get("id", "AGC_003")
    parcel = PARCEL_MAP.get(pid, PARCELS_DB[0])

    base_yield = parcel["rendimiento_pred"] if parcel["rendimiento_pred"] is not None else 3.5

    # Factores de sensibilidad derivados empíricamente de los coeficientes SHAP y del ensamble
    delta_rain_pct = float(data.get("delta_rain_pct", 0.0))    # Variación en lluvia (-40% a +40%)
    delta_dry_days = float(data.get("delta_dry_days", 0.0))    # Días de racha seca adicional (0 a 20)
    delta_ndvi = float(data.get("delta_ndvi", 0.0))            # Variación de vigor NDVI (-0.2 a +0.2)

    # Elasticidades agroclimáticas:
    # 1. Cada +10% de precipitación vegetativa aporta aprox +0.075 t/ha (hasta saturación)
    impact_rain = 0.0075 * delta_rain_pct
    # 2. Cada día extra de racha seca en espigamiento penaliza -0.052 t/ha
    impact_dry = -0.052 * delta_dry_days
    # 3. Cada +0.05 de NDVI en floración aporta +0.14 t/ha
    impact_ndvi = 2.80 * delta_ndvi

    sim_yield = round(max(1.2, min(6.5, base_yield + impact_rain + impact_dry + impact_ndvi)), 4)
    q_90 = MODEL_STATS["metadata"]["conformal_q90"]
    ic_inf = round(max(0.0, sim_yield - q_90), 4)
    ic_sup = round(sim_yield + q_90, 4)

    # Recalcular métricas financieras
    costo_indif = 2.80
    margen_t_ha = round(sim_yield - costo_indif, 2)
    margen_mxn_ha = round(margen_t_ha * 6200, 0)

    if sim_yield >= 4.2:
        riesgo = "BAJO (Riesgo Grado A)"
        color_riesgo = "#10b981"
        recom_credito = "Aprobación Preferencial (Tasa FIRA A+)"
    elif sim_yield >= 3.2:
        riesgo = "MODERADO (Riesgo Grado B)"
        color_riesgo = "#f59e0b"
        recom_credito = "Aprobación Estándar con Seguro Agrícola"
    else:
        riesgo = "ALTO (Riesgo Grado C)"
        color_riesgo = "#ef4444"
        recom_credito = "Requiere Cobertura o Garantía Líquida FEGA"

    return jsonify({
        "id": pid,
        "rendimiento_base": base_yield,
        "rendimiento_simulado": sim_yield,
        "delta_total": round(sim_yield - base_yield, 4),
        "ic90_inf": ic_inf,
        "ic90_sup": ic_sup,
        "impacto_desglosado": {
            "lluvia_t_ha": round(impact_rain, 4),
            "sequia_t_ha": round(impact_dry, 4),
            "vigor_ndvi_t_ha": round(impact_ndvi, 4)
        },
        "finance": {
            "margen_t_ha": margen_t_ha,
            "margen_mxn_ha": margen_monetario_ha,
            "riesgo": riesgo,
            "color_riesgo": color_riesgo,
            "credito_recom": recom_credito
        }
    })


@app.route("/download/entrega_csv")
def download_entrega_csv():
    """Descarga el archivo oficial de 59 parcelas con 4 decimales requerido por las bases."""
    csv_path = ROOT_DIR / "ID_area_rendimiento_70_30_Reto_AgroCebada_ENTREGA.csv"
    if not csv_path.exists():
        csv_path = ROOT_DIR / "resultados" / "ID_area_rendimiento_70_30_Reto_AgroCebada_PREDICCIONES.csv"
    return send_file(str(csv_path), as_attachment=True, download_name="ID_area_rendimiento_70_30_Reto_AgroCebada_ENTREGA.csv")


@app.route("/download/predicciones_completas_csv")
def download_predicciones_completas_csv():
    """Descarga el archivo de predicciones con intervalos de confianza e información municipal."""
    csv_path = ROOT_DIR / "resultados" / "ID_area_rendimiento_70_30_Reto_AgroCebada_PREDICCIONES.csv"
    return send_file(str(csv_path), as_attachment=True, download_name="ID_area_rendimiento_70_30_Reto_AgroCebada_PREDICCIONES.csv")


if __name__ == "__main__":
    print("Iniciando AgroCebada Intelligence Platform...")
    print("Servidor web disponible en: http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
