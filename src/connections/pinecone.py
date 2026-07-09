import time
from pinecone import Pinecone, ServerlessSpec
from src.config import (
    PINECONE_API_KEY, PINECONE_INDEX_NAME, PINECONE_CLOUD, PINECONE_REGION
)
from src.utils.logger import setup_logger

logger = setup_logger("pinecone_connection")

class PineconeConnectionManager:
    """
    Manages connection life-cycle, Serverless Index provisioning,
    and batch queries/upserts for Pinecone Vector Database.
    """
    def __init__(
        self, 
        index_name: str = PINECONE_INDEX_NAME,
        api_key: str = PINECONE_API_KEY
    ):
        self.index_name = index_name
        self.api_key = api_key
        self._pc = None
        self._index = None

    def connect(self) -> Pinecone:
        """
        Creates and returns the Pinecone client.
        """
        if self._pc is not None:
            return self._pc
            
        if not self.api_key:
            raise ValueError(
                "Pinecone API Key is not configured. "
                "Please configure the PINECONE_API_KEY environment variable in your server or secrets settings."
            )
            
        logger.info("Initializing Pinecone client...")
        self._pc = Pinecone(api_key=self.api_key)
        return self._pc

    def get_index(self):
        """
        Returns the instantiated Index client object.
        """
        if self._index is not None:
            return self._index
            
        pc = self.connect()
        self._index = pc.Index(self.index_name)
        return self._index

    def setup_index(self) -> None:
        """
        Checks if the index exists, drops it if present, and provisions
        a Serverless Index configured for 384-dimensional dense vectors
        and supporting sparse-dense hybrid operations.
        """
        pc = self.connect()
        try:
            existing_indexes = [idx.name for idx in pc.list_indexes()]
            if self.index_name in existing_indexes:
                logger.warning(f"Pinecone index '{self.index_name}' already exists. Dropping index to start fresh...")
                pc.delete_index(self.index_name)
        except Exception as e:
            logger.warning(f"Could not list or drop indexes. Detail: {e}")

        logger.info(f"Creating Pinecone Serverless Index '{self.index_name}' ({PINECONE_CLOUD}/{PINECONE_REGION})...")
        pc.create_index(
            name=self.index_name,
            dimension=384,  # BGE-small dense size
            metric="dotproduct",
            spec=ServerlessSpec(
                cloud=PINECONE_CLOUD,
                region=PINECONE_REGION
            )
        )
        
        # Wait for index to become active (critical for immediate upserts)
        logger.info("Waiting for Pinecone index to initialize and become active...")
        while True:
            desc = pc.describe_index(self.index_name)
            if desc.status.get("ready"):
                break
            time.sleep(1)
            
        logger.info(f"Pinecone index '{self.index_name}' is fully ready and online.")
        self._index = pc.Index(self.index_name)

    def upsert_vectors(self, vectors: list) -> None:
        """
        Batch upserts a list of vectors to Pinecone.
        Each item in vectors should be formatted as:
        {
            "id": str,
            "values": list[float],
            "sparse_values": {"indices": list[int], "values": list[float]},
            "metadata": dict
        }
        """
        index = self.get_index()
        index.upsert(vectors=vectors)
        logger.info(f"Successfully upserted {len(vectors)} hybrid points to Pinecone index '{self.index_name}'.")

    def query_hybrid(self, dense_vector: list, sparse_indices: list, sparse_values: list, limit: int = 50) -> list:
        """
        Performs a sparse-dense hybrid query against Pinecone.
        """
        index = self.get_index()
        response = index.query(
            vector=dense_vector,
            sparse_vector={
                "indices": sparse_indices,
                "values": sparse_values
            },
            top_k=limit,
            include_metadata=True
        )
        # Convert Pinecone Match objects to a standard dictionary shape matching our schema
        points = []
        for match in response.matches:
            points.append(
                _PineconeHitWrapper(
                    id=match.id,
                    score=match.score,
                    payload=match.metadata or {}
                )
            )
        return points

class _PineconeHitWrapper:
    """
    Minimal helper class that mocks Qdrant hit structures to keep search.py compatible
    without rewriting query mappings.
    """
    def __init__(self, id: str, score: float, payload: dict):
        self.id = id
        self.score = score
        self.payload = payload
