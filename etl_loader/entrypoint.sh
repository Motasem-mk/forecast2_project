#!/bin/bash
set -euo pipefail

echo "=== Waiting for MongoDB replica set to be ready ==="
python3 -c "
import time
import os
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

mongo_uri = os.getenv('MONGO_URI')
max_retries = 30
retry_delay = 5

for attempt in range(max_retries):
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('hello')
        print(f'MongoDB connected successfully on attempt {attempt + 1}')
        break
    except ServerSelectionTimeoutError:
        print(f'Attempt {attempt + 1}/{max_retries}: MongoDB not ready, retrying in {retry_delay} seconds...')
        time.sleep(retry_delay)
else:
    print('Failed to connect to MongoDB after all retries')
    exit(1)
"

echo "=== Starting transform ==="
python3 transform.py

echo "=== Starting migration ==="
python3 migrate.py

echo "=== Running quality checks ==="
python3 test_quality.py

echo "=== Pipeline complete ==="