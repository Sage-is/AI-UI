from sage_is_ai.retrieval.vector.main import VectorDBBase
from sage_is_ai.retrieval.vector.type import VectorType
from sage_is_ai.config import VECTOR_DB, ENABLE_QDRANT_MULTITENANCY_MODE


class Vector:

    @staticmethod
    def get_vector(vector_type: str) -> VectorDBBase:
        """
        get vector db instance by vector type
        """
        match vector_type:
            case VectorType.MILVUS:
                from sage_is_ai.retrieval.vector.dbs.milvus import MilvusClient

                return MilvusClient()
            case VectorType.QDRANT:
                if ENABLE_QDRANT_MULTITENANCY_MODE:
                    from sage_is_ai.retrieval.vector.dbs.qdrant_multitenancy import (
                        QdrantClient,
                    )

                    return QdrantClient()
                else:
                    from sage_is_ai.retrieval.vector.dbs.qdrant import QdrantClient

                    return QdrantClient()
            case VectorType.PINECONE:
                from sage_is_ai.retrieval.vector.dbs.pinecone import PineconeClient

                return PineconeClient()
            case VectorType.OPENSEARCH:
                from sage_is_ai.retrieval.vector.dbs.opensearch import OpenSearchClient

                return OpenSearchClient()
            case VectorType.ELASTICSEARCH:
                from sage_is_ai.retrieval.vector.dbs.elasticsearch import (
                    ElasticsearchClient,
                )

                return ElasticsearchClient()
            case VectorType.CHROMA:
                from sage_is_ai.retrieval.vector.dbs.chroma import ChromaClient

                return ChromaClient()
            case _:
                raise ValueError(f"Unsupported vector type: {vector_type}")


try:
    VECTOR_DB_CLIENT = Vector.get_vector(VECTOR_DB)
except ImportError:
    VECTOR_DB_CLIENT = None
    import logging
    logging.getLogger(__name__).warning(
        "Vector DB client not available — install required packages via the AI Engine wizard."
    )
