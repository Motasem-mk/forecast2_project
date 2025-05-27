#!/usr/bin/env python3
"""
crud_demo.py

A quick demonstration of all four basic MongoDB CRUD operations
(Create, Read, Update, Delete) using the same `forecast2` database.
This is purely illustrative—does not affect your real `stations`
or `observations` collections.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient

# ───── Logging Setup ─────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ───── Load Env & Connect ─────
load_dotenv()  # expects MONGO_URI in .env
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    logger.error("Missing MONGO_URI in .env")
    sys.exit(1)

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
try:
    client.admin.command("ping")
    logger.info("Connected to MongoDB")
except Exception as e:
    logger.error(f"Cannot connect to MongoDB: {e}")
    sys.exit(1)

db = client.get_default_database()
demo_col = db["crud_demo"]

# ───── 1) CREATE ─────
# Insert a new document with a timestamp and a random value
new_doc = {
    "demo_id": "test123",
    "created_at": datetime.utcnow(),
    "value": 42
}
insert_result = demo_col.insert_one(new_doc)
logger.info(f"Inserted document with _id: {insert_result.inserted_id}")

# ───── 2) READ ─────
# Find that document by our demo_id
found = demo_col.find_one({"demo_id": "test123"})
if found:
    logger.info(f"Read document: {found}")
else:
    logger.error("Document not found!")

# ───── 3) UPDATE ─────
# Change the `value` field
update_result = demo_col.update_one(
    {"demo_id": "test123"},
    {"$set": {"value": 100}}
)
logger.info(f"Matched {update_result.matched_count}, modified {update_result.modified_count}")

# Verify the update
updated = demo_col.find_one({"demo_id": "test123"})
logger.info(f"After update: {updated}")

# ───── 4) DELETE ─────
# Remove the document we just created
delete_result = demo_col.delete_one({"demo_id": "test123"})
logger.info(f"Deleted {delete_result.deleted_count} document(s)")

# Confirm deletion
should_be_none = demo_col.find_one({"demo_id": "test123"})
logger.info(f"After delete, find_one returns: {should_be_none}")

# ───── Cleanup & Exit ─────
client.close()
logger.info("CRUD demo complete. Exiting.")
