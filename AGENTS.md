# Developer & AI Agent Coding Guidelines (AGENTS.md)

This workspace outlines rules and guidelines for developers and AI coding agents editing this codebase.

## Code Style & OOP Architecture

1. **Object-Oriented Design (OOP):**
   - Decouple connections, business logic, routing, and configurations.
   - Avoid global variables or direct service instantiations. Use **Constructor Dependency Injection** (e.g. inject `QdrantConnectionManager` or `SparkSessionManager` into the core services).

2. **Folder Structure Invariants:**
   - `src/connections/`: Houses database and distributed session managers (e.g., Spark, Qdrant client managers).
   - `src/utils/`: Pure calculations, formats, metrics logging, or text chunkers. No stateful connections allowed here.
   - `src/ingestion/` & `src/retrieval/`: Business services implementing the primary pipeline stages.
   - `src/api/`: Routing, schemas, and endpoint request models.

3. **Type Hinting & Validation:**
   - All public methods must include type hints.
   - API payloads must inherit from Pydantic `BaseModel` for validation constraints.

---

## PySpark & Thread Safety Safeguards

> [!CAUTION]
> **MacOS Process Fork Safety:**
> When executing PySpark on macOS Apple Silicon, PyTorch will abort (`SIGABRT`) if native Metal Performance Shaders (MPS) are loaded in forked executor processes.
> - **Rule:** Always pass `device="cpu"` to `SentenceTransformer` and other models when executing inside Spark partitions (`mapPartitions` / UDFs).
> - **Rule:** Maintain `os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"` and `os.environ["TOKENIZERS_PARALLELISM"] = "false"` at application start.

> [!CAUTION]
> **Database File Locking:**
> Local/Embedded vector databases (like `QdrantClient(path=...)` or SQLite) lock database storage files for write operations.
> - **Rule:** Workers/Executors inside parallel Spark partitions must NOT attempt to execute write/upsert operations to local-disk databases.
> - **Rule:** Partition workers should only return computed arrays/vectors. The Spark driver must collect results and execute batch database updates in a single thread.

---

## Git Commit Workflow

1. Always branch off of `main` using structured feature branch names (`feature/` or `bugfix/`).
2. Make logical, clean commits describing modifications clearly.
3. Validate tests (`pytest`) and pipeline execution before merging to `main`.
