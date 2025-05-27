#!/usr/bin/env python3
"""
test_quality.py

Runs data quality checks on the `observations` collection:
- Verifies no duplicate (station_id, timestamp) pairs
- Calculates missing-value rates for each field and fails if any exceed 5%
"""
import os
import sys
import logging
from collections import Counter

from pymongo import MongoClient
from dotenv import load_dotenv

# ───── Logging Setup ─────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ───── Load Environment ─────
load_dotenv()  # reads MONGO_URI from .env

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    logger.error("Missing MONGO_URI in .env")
    sys.exit(1)

# ───── Connect to MongoDB ─────
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    logger.info("Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"Cannot connect to MongoDB: {e}")
    sys.exit(1)

db = client.get_default_database()
obs_col = db["observations"]

# ───── 1) Fetch all observations ─────
all_docs = list(obs_col.find({}, {"station_id": 1, "timestamp": 1, "_id": 0}))
total = len(all_docs)
logger.info(f"Total documents in 'observations': {total}")

# ───── 2) Check duplicates ─────
pairs = [(d["station_id"], d["timestamp"]) for d in all_docs]
dup_counts = Counter(pairs)
dups = sum(1 for c in dup_counts.values() if c > 1)
if dups:
    logger.error(f"Found {dups} duplicate (station_id, timestamp) pairs!")
    sys.exit(2)
logger.info("✅ No duplicate (station_id, timestamp) pairs.")

# ───── 3) Missing-value stats ─────
fields = all_docs[0].keys() if total > 0 else []
logger.info("Missing-value counts and percentages:")
bad = False
for field in fields:
    null_count = obs_col.count_documents({field: {"$in": [None, "", float("nan")]}})
    pct = (null_count / total * 100) if total else 0
    logger.info(f"  {field:15s}: {null_count:5d} / {total:5d} ({pct:5.2f}%)")
    if pct > 5:
        logger.error(f"Field '{field}' exceeds 5% missing values")
        bad = True

if bad:
    sys.exit(3)

logger.info("✅ All fields under 5% missing. Data quality checks passed.")
