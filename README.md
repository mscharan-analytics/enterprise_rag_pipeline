# Enterprise Scale-Ready RAG Prototype

A modular, production-grade, miniaturized prototype of a hybrid vector/keyword Retrieval-Augmented Generation (RAG) pipeline. This pipeline uses PySpark local mode for distributed text ingestion, Qdrant for Reciprocal Rank Fusion (RRF) search, and a Cross-Encoder for Stage 2 reranking. It is designed to model patterns that scale horizontally to 10 million documents.

---

## Technical Stack & Architecture

- **Ingestion Engine:** PySpark (local mode) used to clean text, calculate SHA-256 document IDs (for idempotent updates), and apply recursive character chunking.
- **Embedding Generation:** SentenceTransformers (`bge-small-en-v1.5`) mapped across data partitions on workers.
- **Sparse Indexing:** Stable FNV-1a 32-bit token hashing (custom TF-IDF keyword representation) to support hybrid search without downloading heavy sparse models.
- **Vector DB:** Qdrant Client (supports Docker container deployment or local Embedded in-process storage).
- **Reranker:** Cross-Encoder (`bge-reranker-base`) evaluating the top 50 candidates down to 5 highly relevant contexts.
- **UI:** A Streamlit dashboard showcasing diagnostic latency metrics, Stage 1 RRF candidates, and Stage 2 Reranked results.

---

## Directory Structure

```
enterprise_rag_service/
├── docker-compose.yml       # Configuration for local Qdrant container
├── requirements.txt         # Python project packages
├── app.py                   # Streamlit control panel & UI
├── verify_pipeline.py       # Headless pipeline verification script
├── data/
│   └── generate_data.py     # Programmatic generator for 1,000 messy files
└── src/
    ├── config.py            # Central configurations
    ├── ingestion/
    │   ├── chunker.py       # Recursive character chunking
    │   └── pipeline.py      # PySpark ingestion pipeline
    └── retrieval/
        ├── sparse_encoder.py # Deterministic FNV-1a keyword hashing
        └── search.py        # Hybrid vector RRF search & reranking
```

---

## Quick Start

### 1. Prerequisite Installations
Ensure that **Homebrew** is available on your machine. The pipeline requires Java to run PySpark. Run the following commands to install Java:
```bash
# Install openjdk@17
brew install openjdk@17
```

### 2. Set Up Virtual Environment
Initialize a local Python virtual environment and install the required dependencies:
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Launch Vector Database (Optional)
If you wish to use the Docker-based container mode, start the Qdrant service using Docker Compose:
```bash
docker compose up -d
```
*Note: By default, the application is pre-configured to use **Embedded Mode** (local directory storage at `./qdrant_storage`), which runs fully in Python without requiring Docker. You can toggle this setting in the Streamlit Sidebar.*

### 4. Run the Sandbox UI
Launch the control panel dashboard:
```bash
streamlit run app.py
```

### 5. Ingest & Search
1. In the Streamlit Sidebar, click **🚀 Ingest / Seed Database**. This will automatically generate the 1,000 corporate documents inside the `./data` folder and run the PySpark ingestion job to index them.
2. Click **🔌 Connect/Load Search Engine** to load the neural models into memory.
3. Submit queries in the **Query Sandbox** input box (e.g., *"Find a clinical log mentioning patient Charlie Brown"*).
4. Inspect the **Diagnostics** panel and the **Performance Latency** sidebar to view detailed breakdowns of retrieval vs. reranking timings.

---

## Headless Pipeline Verification
You can also run a headless verification of the entire end-to-end flow from your terminal:
```bash
source .venv/bin/activate
python3 verify_pipeline.py
```
This script runs the database ingestion, loads the models, executes sample queries, and prints latency performance metrics.
