# Módulo de Inferencia Oficial con Modelos Optuna y Residuales Intra-Municipales
import json, pickle
from pathlib import Path
import numpy as np, pandas as pd

WEIGHTS_DIR = Path(__file__).parent

def load_optuna_inference_artifacts():
    with open(WEIGHTS_DIR / "ensemble_metadata_optuna.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    with open(WEIGHTS_DIR / "base_muni_model.pkl", "rb") as f:
        base_muni = pickle.load(f)
    with open(WEIGHTS_DIR / "scaler_ridge.pkl", "rb") as f:
        sc_r = pickle.load(f)
    with open(WEIGHTS_DIR / "model_residual_ridge.pkl", "rb") as f:
        rm_r = pickle.load(f)
    with open(WEIGHTS_DIR / "scaler_svr.pkl", "rb") as f:
        sc_s = pickle.load(f)
    with open(WEIGHTS_DIR / "model_residual_svr.pkl", "rb") as f:
        rm_s = pickle.load(f)
    return meta, base_muni, sc_r, rm_r, sc_s, rm_s

def predict_parcela(muni_vector, sat_vector):
    """
    Realiza la inferencia para una parcela combinando el efecto municipal y residual satelital optimizado.
    
    Parámetros:
    - muni_vector: pd.DataFrame o np.array con las variables dummy del municipio (muni_*)
    - sat_vector: pd.DataFrame con las características numéricas de la parcela
    """
    meta, base_muni, sc_r, rm_r, sc_s, rm_s = load_optuna_inference_artifacts()
    
    # 1. Base municipal
    p_base = base_muni.predict(muni_vector)[0]
    
    # 2. Residual Ridge
    feat_r = meta["features_residual_ridge"]
    X_r = sc_r.transform(sat_vector[feat_r])
    p_res_r = rm_r.predict(X_r)[0]
    
    # 3. Residual SVR
    feat_s = meta["features_residual_svr"]
    X_s = sc_s.transform(sat_vector[feat_s])
    p_res_s = rm_s.predict(X_s)[0]
    
    # Ponderación del ensamble SLSQP
    # [w_base, w_res_r, w_res_s]
    w = meta["weights"][:3]
    w = np.array(w) / np.sum(w)
    pred_final = float(w[0] * p_base + w[1] * (p_base + p_res_r) + w[2] * (p_base + p_res_s))
    
    q_90 = meta["q_90"]
    return {
        "rendimiento_t_ha": round(pred_final, 4),
        "ic_90_inf": round(max(0.0, pred_final - q_90), 4),
        "ic_90_sup": round(pred_final + q_90, 4)
    }

if __name__ == "__main__":
    meta, *_ = load_optuna_inference_artifacts()
    print("Módulo de Inferencia Optuna listo. Métricas CV del ensamble:")
    print(meta["metrics_cv"])
