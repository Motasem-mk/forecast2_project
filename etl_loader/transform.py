#!/usr/bin/env python3
"""
transform.py: Read raw weather data from S3, split into stations metadata and observations,
normalize units, and write back two JSONL files for loading into MongoDB.

This script is organized into clear steps with explanatory comments for non-technical readers.
"""

# ==========================
# Step 1: Setup and Imports
# ==========================
# We load the tools our script uses:
# - logging: to print progress messages with timestamps and diagnostics
# - datetime: to record start and end times of the run
# - boto3: to talk to AWS S3
# - pandas and numpy: to handle tables and numbers
import io
import json
import logging
from datetime import datetime  # used to timestamp script start/end
import boto3
import pandas as pd
import numpy as np

# ==========================
# Step 2: Configuration
# ==========================
# Here we define where to find our raw data in S3,
# and where to write our cleaned files.
BUCKET = "greenandcoop-forecast-raw"
REGION = "eu-west-3"
PREFIXES = {
    "infoclimat":  "raw/infoclimat/",
    "lamadeleine": "raw/weather_underground_lamadeleine_FR/",
    "ichtegem":    "raw/weather_underground_ichtegem_BE/",
}
OUTPUT_STATIONS_KEY     = "staging/stations.jsonl"
OUTPUT_OBSERVATIONS_KEY = "staging/observations.jsonl"

# ==========================
# Step 3: Helper Functions
# ==========================
# These small functions convert units and read JSONL from S3.

def read_jsonl_from_s3(prefix: str) -> pd.DataFrame:
    """
    List objects under `prefix`, pick the first .jsonl file,
    download and return it as a pandas DataFrame.
    """
    logging.info(f"Listing S3 objects under {prefix}")
    s3 = boto3.client("s3", region_name=REGION)
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    key = next(o["Key"] for o in resp.get("Contents", []) if o["Key"].endswith(".jsonl"))
    logging.info(f"Found JSONL file: {key}")
    body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read().decode("utf-8")
    return pd.read_json(io.StringIO(body), lines=True)

def f2c(f_str):
    """Convert a string like '56.2 °F' to Celsius as a float."""
    if not isinstance(f_str, str) or not f_str.strip():
        return np.nan
    f = float(f_str.replace("°F", "").strip())
    return (f - 32) * 5/9

def mph2kmh(mph_str):
    """Convert a string like '4.4 mph' to km/h as a float."""
    if not isinstance(mph_str, str) or not mph_str.strip():
        return np.nan
    m = float(mph_str.replace("mph", "").strip())
    return m * 1.609344

def in2hpa(in_str):
    """Convert a string like '29.75 in' (inches of mercury) to hPa."""
    if not isinstance(in_str, str) or not in_str.strip():
        return np.nan
    i = float(in_str.replace("in", "").strip())
    return i * 33.8639

def in2mm(in_str):
    """Convert a string like '0.19 in' to millimeters."""
    if not isinstance(in_str, str) or not in_str.strip():
        return np.nan
    i = float(in_str.replace("in", "").strip())
    return i * 25.4

# ===================================
# Step 4: Flatten Infoclimat Stations
# ===================================
# We read the nested Infoclimat JSON, extract station metadata,
# and make one observation per hourly record.

def flatten_infoclimat(df_ic: pd.DataFrame):
    stations = {}
    obs_recs = []
    for payload in df_ic.get("_airbyte_data", []):
        for st in payload.get("stations", []):
            sid = st.get("id")
            stations[sid] = {
                "station_id":   sid,
                "station_name": st.get("name"),
                "latitude":     st.get("latitude"),
                "longitude":    st.get("longitude"),
                "elevation":    st.get("elevation"),
                "station_type": st.get("type"),
                "license":      st.get("license"),
            }
        for sid, readings in payload.get("hourly", {}).items():
            if not isinstance(readings, list):
                continue
            for r in readings:
                if not isinstance(r, dict):
                    continue
                obs_recs.append({
                    "station_id":      sid,
                    "timestamp":       r.get("dh_utc"),
                    "temperature":     float(r.get("temperature") or np.nan),
                    "dew_point":       float(r.get("point_de_rosee") or np.nan),
                    "humidity":        float(r.get("humidite") or np.nan),
                    "wind_direction":  int(r.get("vent_direction")) if r.get("vent_direction") else None,
                    "wind_speed":      float(r.get("vent_moyen") or np.nan),
                    "wind_gust":       float(r.get("vent_rafales") or np.nan),
                    "pressure":        float(r.get("pression") or np.nan),
                    "precip_rate":     np.nan,
                    "precip_1h":       float(r.get("pluie_1h") or 0),
                    "visibility":      float(r.get("visibilite") or np.nan),
                    "snow_depth":      float(r.get("neige_au_sol") or np.nan),
                    "cloud_cover":     int(r.get("nebulosite")) if r.get("nebulosite") else None,
                    "present_weather": r.get("temps_omm"),
                    "uv_index":        np.nan,
                    "solar_radiation": np.nan,
                    "source":          "infoclimat",
                })
    df_obs = pd.DataFrame.from_records(obs_recs)
    df_st  = pd.DataFrame.from_records(list(stations.values()))
    return df_obs, df_st

# ===================================
# Step 5: Normalize Weather Underground
# ===================================
# We read the flat WU JSON, attach station metadata, and convert units.

def normalize_wu(df_raw: pd.DataFrame, station_meta: dict):
    df_flat = pd.json_normalize(df_raw.get("_airbyte_data", []))
    records = []
    for rec in df_flat.to_dict(orient="records"):
        if not rec.get("Temperature"):
            continue
        records.append({
            **station_meta,
            "timestamp":       rec.get("Time"),
            "temperature":     f2c(rec.get("Temperature")),
            "dew_point":       f2c(rec.get("Dew Point")),
            "humidity":        float(str(rec.get("Humidity","0")).replace("%","")),
            "wind_direction":  rec.get("Wind"),
            "wind_speed":      mph2kmh(rec.get("Speed")),
            "wind_gust":       mph2kmh(rec.get("Gust")),
            "pressure":        in2hpa(rec.get("Pressure")),
            "precip_rate":     np.nan,
            "precip_1h":       in2mm(rec.get("Precip. Accum.") or "0in"),
            "visibility":      np.nan,
            "snow_depth":      np.nan,
            "cloud_cover":     np.nan,
            "present_weather": None,
            "uv_index":        float(rec.get("UV") or np.nan),
            "solar_radiation": float(str(rec.get("Solar","0 w/m²")).replace("w/m²","")),
            "source":          "weather_underground",
        })
    return pd.DataFrame.from_records(records)

# ==========================
# Step 6: Main Flow
# ==========================
def main():
    # 1) Configure logging and record start time
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    start_time = datetime.now()
    logging.info(f"--- transform.py started at {start_time.isoformat()} ---")

    # 2) Create an S3 client and log its region
    s3 = boto3.client("s3", region_name=REGION)
    logging.info(f"Using S3 client in region: {s3.meta.region_name}")

    # 3) Read raw inputs
    df_ic  = read_jsonl_from_s3(PREFIXES["infoclimat"])
    df_lm  = read_jsonl_from_s3(PREFIXES["lamadeleine"])
    df_ig  = read_jsonl_from_s3(PREFIXES["ichtegem"])

    # 4) Transform each source
    obs_ic, st_ic = flatten_infoclimat(df_ic)
    meta_lm = {"station_id":"ILAMAD25","station_name":"La Madeleine","latitude":50.7,"longitude":3.1,"elevation":18,"station_type":"weather_underground","license":{"source":"custom"}}
    meta_ig = {"station_id":"IICHTE19","station_name":"WeerstationBS","latitude":50.9,"longitude":2.9,"elevation":22,"station_type":"weather_underground","license":{"source":"custom"}}
    obs_lm = normalize_wu(df_lm, meta_lm)
    obs_ig = normalize_wu(df_ig, meta_ig)

    # 5) Combine station metadata and remove duplicates
    df_stations = pd.concat([st_ic, pd.DataFrame([meta_lm, meta_ig])], ignore_index=True)
    df_stations = df_stations.drop_duplicates(subset=["station_id"]).reset_index(drop=True)

    # 6) Combine all observations
    df_observations = pd.concat([obs_ic, obs_lm, obs_ig], ignore_index=True)

    # 7) Write out JSONL files to S3 with diagnostic logging
    logging.info(f"Writing {len(df_stations)} stations to {OUTPUT_STATIONS_KEY}")
    resp_st = s3.put_object(
        Bucket=BUCKET,
        Key=OUTPUT_STATIONS_KEY,
        Body=df_stations.to_json(orient="records", lines=True).encode("utf-8")
    )
    logging.info(f"PutObject stations response: {resp_st}")

    logging.info(f"Writing {len(df_observations)} observations to {OUTPUT_OBSERVATIONS_KEY}")
    resp_obs = s3.put_object(
        Bucket=BUCKET,
        Key=OUTPUT_OBSERVATIONS_KEY,
        Body=df_observations.to_json(orient="records", lines=True).encode("utf-8")
    )
    logging.info(f"PutObject observations response: {resp_obs}")

    # 8) List staging/ contents to verify
    listing = s3.list_objects_v2(Bucket=BUCKET, Prefix="staging/")
    keys = [o["Key"] for o in listing.get("Contents", [])]
    logging.info(f"S3 staging/ contents: {keys}")

    # 9) Record end time and duration
    end_time = datetime.now()
    duration = end_time - start_time
    logging.info(f"--- transform.py completed at {end_time.isoformat()} (duration: {duration}) ---")

if __name__ == "__main__":
    main()
