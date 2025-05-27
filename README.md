# Forecast2 Project

This repository contains the end-to-end data pipeline for the Forecast 2.0 project at GreenAndCoop, integrating new weather data sources into a MongoDB database on AWS. The pipeline ingests raw data via Airbyte, transforms it with Python, tests its quality, and loads it into a replicated MongoDB cluster running on ECS Fargate.

---

## Table of Contents

1. [Context & Mission](#context--mission)
2. [Data Sources](#data-sources)
3. [Architecture & Flowchart](#architecture--flowchart)
4. [Local Development](#local-development)
5. [AWS Deployment](#aws-deployment)
6. [Scripts & Components](#scripts--components)
7. [Quality & Monitoring](#quality--monitoring)
8. [Prerequisites & Tools](#prerequisites--tools)
9. [License & Acknowledgments](#license--acknowledgments)

---

## Context & Mission

GreenAndCoop needs precise, reliable weather data to improve its electricity demand forecasting. Forecast 2.0 enriches existing models with new semi-professional and amateur station feeds.

> **Challenge**: Integrate multiple heterogeneous sources (JSON, Excel) into a unified MongoDB schema, automate ETL, ensure data quality, and deploy on AWS for daily refresh.

## Data Sources

* **Infoclimat (France)**

  * Static network stations: Bergues, Hazebrouck, Armentières, Lille-Lesquin
  * URL (S3 JSON): `s3://course.oc-static.com/.../Data_Source1_011024-071024.json`
* **Weather Underground (Amateur)**

  * Station ILAMAD25 (La Madeleine, FR)
  * Station IICHTE19 (Ichtegem, BE)

> **Ingestion**: We use [Airbyte](https://airbyte.com/) to pull JSON and Excel sources into `s3://greenandcoop-forecast-raw/raw/…`.

## Architecture & Flowchart

Below is the high‑level flowchart of the ETL pipeline. You can find the source diagram in `docs/flowchart.drawio.png` (or view the exported image at `docs/flowchart.png`).

![ETL Flowchart](docs/flowchart.png)

*Steps in the flowchart:*

1. **Airbyte Ingestion** – raw JSON and Excel data pulled into `s3://greenandcoop-forecast-raw/raw/…`
2. **transform.py** – flatten, normalize, and split into two JSONL files in `s3://…/staging/`
3. **migrate.py** – upsert into MongoDB `stations` and `observations` collections
4. **test\_quality.py** – automated quality checks (duplicates, missing rates)
5. **crud\_demo.py** – demonstration of Create/Read/Update/Delete in MongoDB
6. **Entry & Scheduling** – Docker/ECS orchestration and query‑latency monitoring

## Environment Configuration

All runtime settings are driven by environment variables. A sample file `etl_loader/.env.example` shows the required entries:

```text
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=eu-west-3
S3_BUCKET=greenandcoop-forecast-raw
MONGO_INITDB_ROOT_USERNAME=etl_user
MONGO_INITDB_ROOT_PASSWORD=aws
MONGO_URI=mongodb://etl_user:aws@mongo1:27017,mongo2:27017,mongo3:27017/forecast2?replicaSet=rs0&authSource=admin
```

When running locally with Docker Compose, copy `.env.example` to `.env` in the project root. On AWS/ECS, configure these values as Task Definition **environment** and **Secret** entries (via Parameter Store or Secrets Manager).

## Local Development

These steps let you run the full pipeline on your local machine using Docker Compose:

1. **Clone the repository**

   ```bash
   git clone https://github.com/Motasem-mk/forecast2_project.git
   cd forecast2_project
   ```

2. **Copy the environment template**

   ```bash
   cp etl_loader/.env.example .env
   ```

   Then edit `.env` and fill in your AWS credentials, MongoDB root username/password, and S3 bucket name.

3. **Install Docker & Docker Compose**

   * [Docker Desktop](https://www.docker.com/products/docker-desktop) on macOS/Windows
   * `docker-compose` on Linux via your package manager

4. **Start the services**

   ```bash
   docker-compose up --build
   ```

   This will spin up:

   * A 3-node MongoDB replica set (mongodb://localhost:27017/forecast2)
   * The ETL container which runs: `transform.py`, `migrate.py`, `test_quality.py`, and `crud_demo.py`.

5. **Verify**

   * Open a new terminal and connect to MongoDB:

     ```bash
     docker exec -it mongo1 mongosh -u <root_user> -p <root_password> --authenticationDatabase admin
     ```
   * Check the `stations` and `observations` collections:

     ```js
     use forecast2;
     db.stations.count();
     db.observations.count();
     ```

6. **Stopping**

   ```bash
   docker-compose down
   ```

---

## AWS Deployment

1. **ECR**: Push `etl_loader` image (and optionally mirror `mongo:6.0`).
2. **Parameter Store**: Store `mongo-keyfile` and sensitive ENV as SecureStrings.
3. **ECS Cluster**: Create Fargate cluster and EFS volumes (or EBS via EC2) for Mongo data.
4. **Task Definition**: Define 3 Mongo containers + init + ETL container, inject env/secrets.
5. **Service**: Launch replica set service; verify with `rs.status()`.
6. **Scheduled Task**: Trigger ETL pipeline daily or on demand; logs to CloudWatch.

## Scripts & Components

* `transform.py`: read raw S3 JSONL, normalize units, write staging JSONL
* `migrate.py`: load staging JSONL into MongoDB (`stations` + `observations`)
* `test_quality.py`: data-quality assertions (duplicates, missing rates)
* `crud_demo.py`: demonstration of Create, Read, Update, Delete operations
* `entrypoint.sh`: orchestrates the above inside the ETL container
* `docker-compose.yml`: local multi-container setup (3× Mongo + ETL)

## Quality & Monitoring

* **Post-migration quality**: `test_quality.py` fails if >5% missing values or duplicates
* **Accessibility metric**: sample query latency measured in ETL container, logs to CloudWatch
* **Backups**: AWS Backup plan for EFS/EBS snapshots daily
* **Monitoring**: CloudWatch dashboards & alarms for CPU, disk, query latency

## Prerequisites & Tools

* **Airbyte** for ingestion
* **Python 3.10** with `pandas, boto3, pymongo, python-dotenv, pytest`
* **MongoDB 6.0** with replica-set on Docker / ECS Fargate
* **AWS**: S3, ECR, ECS/Fargate, EFS/EC2-EBS, Parameter Store / Secrets Manager, Backup, CloudWatch

## License & Acknowledgments

* Project by GreenAndCoop Data Engineering team
* Course: Master NoSQL Databases & Optimize Your Deployment with Docker
* Data from InfoClimat (CC BY), Weather Underground, and Airbyte

---

*README generated on 2025-05-27*
