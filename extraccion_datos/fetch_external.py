"""Descarga de datos EXTERNOS REALES (no simulados) y cacheo en datos_externos/.

Fuentes (todas publicas y gratuitas):
  * Open-Meteo Historical Weather API (reanalisis ERA5 / ERA5-Land, ECMWF): Tmax, Tmin, precipitacion,
    ET0 FAO-56, radiacion de onda corta, diaria 2022-2025, para la celda de ~0.1 grados de cada parcela.
  * ISRIC SoilGrids v2.0 (REST): propiedades edaficas (arcilla, arena, limo, pH, COS, N, CEC, densidad aparente,
    fragmentos gruesos) a 0-5, 5-15, 15-30 y 30-60 cm, en el centroide de cada parcela (~250 m).
"""
import os, time, json, requests, numpy as np, pandas as pd, geopandas as gpd

BASE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
OUT = os.path.join(BASE, "datos_externos"); os.makedirs(OUT, exist_ok=True)
SHP = os.path.join(BASE, "DATASET_RETO_AGRO_2026", "_ext", "Parcelas_Reto_AGC_CONJUNTO_70_30", "Parcelas_Reto_AGC_CONJUNTO.shp")


def centroides():
    g = gpd.read_file(SHP, encoding="latin1").rename(columns={"ID_POLIGON": "ID_POLIGONO"})
    c = g.to_crs(6372).geometry.centroid.to_crs(4326)
    return pd.DataFrame({"ID_POLIGONO": g.ID_POLIGONO, "lon": c.x, "lat": c.y})


def get_json(url, params, tries=6, wait=20):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=120)
            if r.status_code == 200:
                return r.json()
            print("  HTTP", r.status_code, r.text[:120])
        except Exception as e:
            print("  err", e)
        time.sleep(wait * (i + 1))
    return None


def fetch_openmeteo(df):
    f = os.path.join(OUT, "openmeteo_diario_2022_2025.csv")
    if os.path.exists(f):
        return pd.read_csv(f, parse_dates=["fecha"])
    df = df.assign(clat=(df.lat * 10).round() / 10, clon=(df.lon * 10).round() / 10)
    cells = df[["clat", "clon"]].drop_duplicates()
    daily = ["temperature_2m_max", "temperature_2m_min", "temperature_2m_mean", "precipitation_sum",
             "et0_fao_evapotranspiration", "shortwave_radiation_sum", "wind_speed_10m_max"]
    rows = []
    for _, c in cells.iterrows():
        js = get_json("https://archive-api.open-meteo.com/v1/archive", dict(
            latitude=c.clat, longitude=c.clon, start_date="2022-01-01", end_date="2025-12-31",
            daily=",".join(daily), timezone="America/Mexico_City"))
        d = pd.DataFrame(js["daily"]).rename(columns={"time": "fecha"})
        d["clat"], d["clon"], d["elev_om"] = c.clat, c.clon, js.get("elevation")
        rows.append(d); time.sleep(3)
    out = pd.concat(rows); out.to_csv(f, index=False)
    out["fecha"] = pd.to_datetime(out["fecha"])
    df[["ID_POLIGONO", "clat", "clon"]].to_csv(os.path.join(OUT, "openmeteo_celda_por_parcela.csv"), index=False)
    return out


PROPS = ["clay", "sand", "silt", "phh2o", "soc", "nitrogen", "cec", "bdod", "cfvo"]
DEPTHS = ["0-5cm", "5-15cm", "15-30cm", "30-60cm"]


def fetch_soilgrids(df):
    f = os.environ.get("AGRO_SOIL_FILE") or os.path.join(OUT, "soilgrids_por_parcela.csv")
    if os.path.exists(f):
        return pd.read_csv(f)
    df = df.assign(slat=df.lat.round(2), slon=df.lon.round(2))
    cells = df[["slat", "slon"]].drop_duplicates().reset_index(drop=True)
    cache_f = os.path.join(OUT, "_soilgrids_celdas_parcial.csv")
    done = pd.read_csv(cache_f) if os.path.exists(cache_f) else pd.DataFrame()
    recs = done.to_dict("records")
    have = set(zip(done.slat, done.slon)) if len(done) else set()
    for i, c in cells.iterrows():
        if (c.slat, c.slon) in have:
            continue
        # consulta en el centroide medio de la celda para ser fiel a ~1 km
        sub = df[(df.slat == c.slat) & (df.slon == c.slon)]
        lat, lon = sub.lat.mean(), sub.lon.mean()
        js = get_json("https://rest.isric.org/soilgrids/v2.0/properties/query",
                      [("lon", lon), ("lat", lat)] + [("property", p) for p in PROPS] +
                      [("depth", d) for d in DEPTHS] + [("value", "mean")])
        rec = {"slat": c.slat, "slon": c.slon}
        if js is not None:
            for L in js["properties"]["layers"]:
                dfac = L["unit_measure"]["d_factor"]
                for dep in L["depths"]:
                    v = dep["values"]["mean"]
                    rec[f"sg_{L['name']}_{dep['label'].replace('cm', '')}"] = None if v is None else v / dfac
        recs.append(rec)
        pd.DataFrame(recs).to_csv(cache_f, index=False)
        print(f"soilgrids {i + 1}/{len(cells)}", flush=True)
        time.sleep(13)  # limite publico: 5 consultas/minuto
    sg = pd.DataFrame(recs)
    out = df[["ID_POLIGONO", "slat", "slon"]].merge(sg, on=["slat", "slon"], how="left").drop(columns=["slat", "slon"])
    out.to_csv(f, index=False)
    return out


if __name__ == "__main__":
    c = centroides()
    om = fetch_openmeteo(c); print("openmeteo", om.shape, om.groupby(["clat", "clon"]).ngroups, "celdas")
    sg = fetch_soilgrids(c); print("soilgrids", sg.shape)
