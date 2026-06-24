# Construisez et testez une infrastructure de données

This repository contains the end-to-end data pipeline for the **Forecast 2.0** project at **GreenAndCoop**.

The project integrates new weather data sources into a MongoDB-based data infrastructure on AWS. The pipeline ingests raw data via Airbyte, stores it in Amazon S3, transforms it with Python, tests data quality, and loads the cleaned data into a replicated MongoDB database for analytical use.

This repository documents the validated version of the project, based on an **Airbyte → S3 → Python ETL → MongoDB → AWS** architecture.

---

## Table of Contents

1. [Context & Mission](#context--mission)
2. [Data Sources](#data-sources)
3. [Architecture & Pipeline](#architecture--pipeline)
4. [Repository Structure](#repository-structure)
5. [Environment Configuration](#environment-configuration)
6. [Local Development](#local-development)
7. [AWS Deployment](#aws-deployment)
8. [Scripts & Components](#scripts--components)
9. [Quality & Monitoring](#quality--monitoring)
10. [Prerequisites & Tools](#prerequisites--tools)
11. [Project Deliverable](#project-deliverable)
12. [Author](#author)

---

## Context & Mission

GreenAndCoop is a renewable electricity provider that needs reliable weather data to improve its electricity demand forecasting models.

Forecast 2.0 aims to enrich existing forecasting models with new semi-professional and amateur weather station feeds.

The main challenge was to integrate heterogeneous weather data sources, automate the ETL pipeline, ensure data quality, and deploy a resilient data infrastructure on AWS.

The project objectives were to:

* ingest raw weather data from multiple sources;
* store raw files in Amazon S3;
* transform and standardize heterogeneous data formats;
* load clean data into MongoDB;
* validate data quality automatically;
* deploy a resilient MongoDB replica set;
* monitor the infrastructure and configure backups.

---

## Data Sources

The project uses weather data from multiple sources:

### InfoClimat

Weather stations in France:

* Bergues;
* Hazebrouck;
* Armentières;
* Lille-Lesquin.

### Weather Underground

Amateur weather stations:

* ILAMAD25 — La Madeleine, France;
* IICHTE19 — Ichtegem, Belgium.

The raw data includes heterogeneous formats such as JSONL and Excel files.

Airbyte was used to ingest the raw data into Amazon S3.

---

## Architecture & Pipeline

The ETL pipeline follows this high-level flow:

```text id="szgu8u"
Airbyte → Amazon S3 Raw Zone → Python ETL → S3 Staging Zone → MongoDB Replica Set → Quality Checks → Monitoring
```

Main pipeline steps:

1. Airbyte ingests raw weather data into Amazon S3.
2. `transform.py` reads raw data from S3, flattens and standardizes it.
3. The transformed data is split into station metadata and weather observations.
4. `migrate.py` loads the cleaned data into MongoDB.
5. `test_quality.py` validates duplicates, missing values and document counts.
6. MongoDB stores the data in replicated collections.
7. AWS monitoring and backup mechanisms improve resilience.

The MongoDB database contains two main collections:

* `stations`;
* `observations`.

---

## Repository Structure

```text id="fc40yf"
forecast2_project/
├── README.md
├── docker-compose.yml
├── .gitignore
├── etl_loader/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── transform.py
│   ├── migrate.py
│   ├── test_quality.py
│   └── requirements.txt
└── presentation/
    └── project8-Construisez_et_testez_une_infrastructure_de_donnees_Motasem_Abualqumboz.pptx
```

---

## Environment Configuration

Runtime settings are managed through environment variables.

A local `.env` file can be used for development, but it must not be committed to GitHub.

Example variables:

```text id="oe87re"
AWS_ACCESS_KEY_ID=<your_access_key>
AWS_SECRET_ACCESS_KEY=<your_secret_key>
AWS_REGION=eu-west-3
S3_BUCKET=<your_s3_bucket>

MONGO_INITDB_ROOT_USERNAME=<mongo_root_user>
MONGO_INITDB_ROOT_PASSWORD=<mongo_root_password>

MONGO_URI=mongodb://<user>:<password>@mongo1:27017,mongo2:27017,mongo3:27017/forecast2?replicaSet=rs0&authSource=admin
```

On AWS, sensitive values should be stored using a secure mechanism such as AWS Secrets Manager or Parameter Store.

---

## Local Development

These steps allow the pipeline to be tested locally with Docker Compose.

### 1. Clone the repository

```bash id="s4zqur"
git clone https://github.com/Motasem-mk/forecast2_project.git
cd forecast2_project
```

### 2. Create the environment file

Create a local `.env` file and add the required variables.

Do not commit this file to GitHub.

### 3. Start the local services

```bash id="imxq85"
docker-compose up --build
```

This starts:

* a local MongoDB replica set;
* the ETL container.

The ETL workflow runs:

```text id="4dkhg8"
transform.py → migrate.py → test_quality.py
```

### 4. Verify MongoDB data

Connect to MongoDB and check the collections:

```javascript id="zg4fvy"
use forecast2;
db.stations.countDocuments();
db.observations.countDocuments();
```

### 5. Stop the services

```bash id="sn28e4"
docker-compose down
```

---

## AWS Deployment

The validated AWS architecture includes:

* Amazon S3 for raw and staging data;
* Amazon VPC for network isolation;
* a public subnet for the bastion host and NAT Gateway;
* a private subnet for MongoDB nodes and ECS tasks;
* EC2 instances for the MongoDB replica set;
* EBS volumes for MongoDB persistent storage;
* Amazon ECR for the ETL Docker image;
* Amazon ECS Fargate for running the ETL container;
* CloudWatch for logs, metrics and alarms;
* EBS snapshot policy for automated MongoDB backups.

MongoDB nodes are deployed in private subnets and are not directly exposed to the public internet.

---

## Scripts & Components

### `transform.py`

Reads raw weather files, normalizes data, standardizes fields and prepares cleaned outputs.

### `migrate.py`

Loads the transformed data into MongoDB using upsert logic.

Target collections:

* `stations`;
* `observations`.

### `test_quality.py`

Runs automated data quality checks, including:

* duplicate checks;
* missing-value checks;
* expected document counts;
* MongoDB accessibility checks.

### `entrypoint.sh`

Orchestrates the ETL workflow inside the Docker container.

### `docker-compose.yml`

Defines the local test environment with MongoDB and the ETL container.

---

## Quality & Monitoring

The project includes automated checks and monitoring mechanisms.

Main quality results:

* 6 station records;
* 4,950 weather observation records;
* 1,722 insertions;
* 3,228 updates;
* 0 duplicate `(station_id, timestamp)` pairs;
* all fields below the 5% missing-value threshold;
* successful accessibility checks on MongoDB collections.

The loading stage took approximately 8 seconds.

Monitoring and resilience mechanisms include:

* CloudWatch logs for ETL execution;
* CloudWatch alarms for MongoDB node CPU usage;
* EBS snapshots for automated daily backups;
* 7-day snapshot retention policy.

---

## Prerequisites & Tools

Main tools and services used:

* Airbyte;
* Amazon S3;
* Python;
* MongoDB 6.0;
* Docker;
* Docker Compose;
* Amazon VPC;
* Amazon EC2;
* Amazon EBS;
* Amazon ECR;
* Amazon ECS Fargate;
* Amazon CloudWatch;
* AWS backup snapshots.

Python libraries used by the ETL include:

* pandas;
* boto3;
* pymongo;
* python-dotenv.

---

## Project Deliverable

The official project deliverable was the PowerPoint presentation.

The presentation documents:

* the project context;
* Airbyte ingestion;
* S3 raw data storage;
* local Docker testing;
* MongoDB collections and schemas;
* AWS architecture;
* MongoDB replica set deployment;
* ECR and ECS Fargate deployment;
* automated backups;
* data quality checks;
* query latency analysis;
* CloudWatch monitoring.

The repository contains the supporting ETL files used to demonstrate the validated solution.

---

## Security Note

Sensitive files must not be committed to GitHub.

Do not commit:

```text id="swjhce"
.env
config.json
mongo-keyfile
AWS credentials
real passwords
```

Use example files only when needed:

```text id="3h597x"
.env.example
config.example.json
mongo-keyfile.example
```

---

## Author

Motasem Abualqumboz

Data Engineer
