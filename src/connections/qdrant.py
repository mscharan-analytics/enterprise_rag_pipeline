from qdrant_client import QdrantClient
from qdrant_client import models
from src.config import (
    USE_EMBEDDED_QDRANT, QDRANT_URL, QDRANT_STORAGE_PATH, COLLECTION_NAME
)
from src.utils.logger import setup_logger

logger = setup_logger("qdrant_connection")

class QdrantConnectionManager:
    """
    Manages connection life-cycle, schema initialization, and client actions
    for the Qdrant Vector Database (both in Docker-based and Embedded/disk modes).
    """
    def __init__(self, collection_name: str = COLLECTION_NAME):
        self.collection_name = collection_name
        self._client = None
        
    def connect(self) -> QdrantClient:
        """
        Creates and returns a client connection to Qdrant based on configs.
        """
        if self._client is not None:
            return self._client
            
        if USE_EMBEDDED_QDRANT:
            logger.info(f"Connecting to Qdrant in Embedded mode (disk-bound) at path: '{QDRANT_STORAGE_PATH}'")
            self._client = QdrantClient(path=QDRANT_STORAGE_PATH)
        else:
            logger.info(f"Connecting to Qdrant container server at: '{QDRANT_URL}'")
            self._client = QdrantClient(url=QDRANT_URL)
            
        return self._client

    def setup_collection(self) -> None:
        """
        Ensures the collection exists with the exact named dense/sparse vector fields
        and scalar quantization configured. Re-creates the collection if it exists.
        """
        client = self.connect()
        try:
            collections = client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if exists:
                logger.warning(f"Collection '{self.collection_name}' already exists. Dropping and re-creating...")
                client.delete_collection(self.collection_name)
        except Exception as e:
            logger.warning(f"Could not list collections. Initializing table structure. Details: {e}")

        # Setup collection with Dual-Vector (Dense + Sparse) Schema & Scalar Quantization
        client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                "text-dense": models.VectorParams(
                    size=384,  # BGE-small dimensions
                    distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                "text-sparse": models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False)
                )
            },
            quantization_config=models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(
                    type=models.ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True
                )
            )
        )
        logger.info(f"Successfully initialized collection '{self.collection_name}' with Scalar Quantization.")

    def get_collection_info(self):
        """
        Retrieves schema status.
        """
        client = self.connect()
        return client.get_collection(self.collection_name)

    def upsert_points(self, points: list) -> None:
        """
        Sequentially inserts a list of PointStruct points in batch.
        """
        client = self.connect()
        client.upsert(collection_name=self.collection_name, points=points)
        logger.info(f"Upserted {len(points)} vectors to Qdrant collection '{self.collection_name}'.")

    def query_rrf(self, dense_query: list, sparse_indices: list, sparse_values: list, limit: int = 50) -> list:
        """
        Queries Qdrant using dual-stage Reciprocal Rank Fusion (RRF) for hybrid search.
        """
        client = self.connect()
        prefetch = [
            models.Prefetch(
                query=dense_query,
                using="text-dense",
                limit=limit
            ),
            models.Prefetch(
                query=models.SparseVector(
                    indices=sparse_indices,
                    values=sparse_values
                ),
                using="text-sparse",
                limit=limit
            )
        ]
        
        response = client.query_points(
            collection_name=self.collection_name,
            prefetch=prefetch,
            query=models.FusionQuery(
                fusion=models.Fusion.RRF
            ),
            limit=limit
        )
        return response.points
