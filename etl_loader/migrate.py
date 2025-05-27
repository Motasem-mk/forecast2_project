#!/usr/bin/env python3
"""
migrate.py: Read cleaned JSONL files from S3 and load them into MongoDB.

Overview (for non-technical readers):
1. **Setup & Imports**: Load libraries for logging, AWS access, MongoDB connection, and data handling.
2. **Configuration**: Read environment variables for AWS, S3, and MongoDB settings.
3. **Helper Functions**: Define a function to read JSONL from S3 into a pandas DataFrame.
4. **Database Connections**: Connect to AWS S3 and MongoDB.
5. **Upsert Stations**: Read station metadata and write one document per station into the `stations` collection.
6. **Upsert Observations**: Read observation records and bulk-upsert them into the `observations` collection, keyed by station and timestamp.
7. **Summary & Cleanup**: Log counts of inserted/updated documents and close connections.

Each section includes plain-language comments to explain its purpose.
"""

# ==========================
# Step 1: Setup & Imports
# ==========================
import os
import json
import logging
from datetime import datetime  # for marking start/end times
from dotenv import load_dotenv   # to load AWS and Mongo credentials
import boto3                     # AWS SDK to read S3 files
import pandas as pd              # to handle JSONL files as tables
from pymongo import MongoClient, UpdateOne  # for MongoDB operations

# ==========================
# Step 2: Configuration
# ==========================
# Load environment variables from a .env file in the same directory
load_dotenv()

# Read AWS and MongoDB settings from the environment
AWS_REGION = os.getenv("AWS_REGION", "eu-west-3")
S3_BUCKET  = os.getenv("S3_BUCKET", "greenandcoop-forecast-raw")
STATIONS_KEY     = os.getenv("STATIONS_KEY", "staging/stations.jsonl")
OBSERVATIONS_KEY = os.getenv("OBSERVATIONS_KEY", "staging/observations.jsonl")
MONGO_URI  = os.getenv("MONGO_URI")

# Ensure the MongoDB URI is provided
if not MONGO_URI:
    raise SystemExit("Missing MONGO_URI in environment. Please set it in .env.")

# ==========================
# Step 3: Helper Functions
# ==========================
def read_jsonl_from_s3(bucket: str, key: str) -> pd.DataFrame:
    """
    Download a line-delimited JSON file from S3 and return it as a pandas DataFrame.
    Each line in the file is parsed as one JSON object (one row in the table).
    """
    s3 = boto3.client("s3", region_name=AWS_REGION)
    logging.info(f"Downloading {key} from S3 bucket {bucket}")
    obj = s3.get_object(Bucket=bucket, Key=key)
    body = obj['Body'].read().decode('utf-8')
    # pandas can read JSONL directly
    df = pd.read_json(pd.io.common.StringIO(body), lines=True)
    logging.info(f"Loaded {len(df)} records from {key}")
    return df

# ==========================
# Step 4: Main Flow: Setup Connections
# ==========================
def main():
    # Configure logging to show timestamps
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    start_time = datetime.now()
    logging.info(f"--- Starting migrate.py at {start_time.isoformat()} ---")

    # Connect to MongoDB
    logging.info("Connecting to MongoDB")
    client = MongoClient(MONGO_URI)
    db = client.get_default_database()
    stations_col    = db['stations']
    observations_col = db['observations']

    # ==========================
    # Step 5: Upsert Stations Metadata
    # ==========================
    # Read station metadata from S3
    df_stations = read_jsonl_from_s3(S3_BUCKET, STATIONS_KEY)

    # For each row (one station), upsert into MongoDB
    stations_upserted = 0
    for idx, row in df_stations.iterrows():
        # Build a filter to find existing station by its unique station_id
        filter_ = { 'station_id': row['station_id'] }
        # Convert row to plain dict for MongoDB
        doc = row.to_dict()
        # Upsert: insert if new, or update existing document
        result = stations_col.update_one(
            filter_,
            { '$set': doc },
            upsert=True
        )
        stations_upserted += int(result.upserted_id is not None)
    logging.info(f"Upserted {stations_upserted} new station documents")

    # ==========================
    # Step 6: Bulk Upsert Observations
    # ==========================
    # Read observations from S3
    df_obs = read_jsonl_from_s3(S3_BUCKET, OBSERVATIONS_KEY)

    # Prepare bulk operations: one UpdateOne per record
    ops = []
    for idx, rec in df_obs.iterrows():
        # Unique key: combination of station_id + timestamp
        filter_ = {
            'station_id': rec['station_id'],
            'timestamp': rec['timestamp']
        }
        # Full record for upsert
        update_ = { '$set': rec.to_dict() }
        ops.append(UpdateOne(filter_, update_, upsert=True))

    # Execute bulk write (unordered for speed)
    if ops:
        result = observations_col.bulk_write(ops, ordered=False)
        inserted = result.upserted_count
        modified = result.modified_count
        logging.info(f"Observations bulk write: {inserted} inserted, {modified} modified")
    else:
        logging.info("No observations to write")

    # ==========================
    # Step 7: Summary & Cleanup
    # ==========================
    end_time = datetime.now()
    duration = end_time - start_time
    logging.info(f"--- migrate.py completed at {end_time.isoformat()} (duration: {duration}) ---")
    # Close MongoDB connection
    client.close()

if __name__ == '__main__':
    main()
