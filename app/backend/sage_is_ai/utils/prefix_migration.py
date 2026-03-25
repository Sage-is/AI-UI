"""
Prefix migration utility for renaming service keys/collections from
"open-webui" / "open_webui" to "sage-is-ai" / "sage_is_ai".

All functions are idempotent — safe to run repeatedly on startup.
"""

import logging

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------

async def migrate_redis_prefixes(redis_client) -> int:
    """
    Scan for keys with the old 'open-webui:' prefix and RENAME them
    to 'sage-is-ai:'.  Skips keys where the target already exists.
    Returns the number of keys migrated.
    """
    if redis_client is None:
        return 0

    migrated = 0
    old_prefix = "open-webui:"
    new_prefix = "sage-is-ai:"
    cursor = 0

    try:
        while True:
            cursor, keys = await redis_client.scan(
                cursor=cursor, match=f"{old_prefix}*", count=200
            )
            for key in keys:
                key_str = key if isinstance(key, str) else key.decode()
                new_key = new_prefix + key_str[len(old_prefix):]
                # Only rename if target does not already exist
                if not await redis_client.exists(new_key):
                    await redis_client.rename(key_str, new_key)
                    migrated += 1
            if cursor == 0:
                break
    except Exception as e:
        log.warning(f"Redis prefix migration error (non-fatal): {e}")

    if migrated:
        log.info(f"Redis prefix migration: renamed {migrated} keys")
    return migrated


# ---------------------------------------------------------------------------
# Qdrant
# ---------------------------------------------------------------------------

def migrate_qdrant_prefixes():
    """
    Create aliases from new collection names to old collection names.
    This way queries using new names still hit the existing data.
    """
    try:
        from sage_is_ai.config import VECTOR_DB
        if VECTOR_DB != "qdrant":
            return

        from sage_is_ai.config import (
            QDRANT_URI, QDRANT_API_KEY, QDRANT_COLLECTION_PREFIX,
        )
        from qdrant_client import QdrantClient

        client = QdrantClient(url=QDRANT_URI, api_key=QDRANT_API_KEY)
        collections = {c.name for c in client.get_collections().collections}

        old_prefix = "open-webui"
        new_prefix = QDRANT_COLLECTION_PREFIX  # "sage-is-ai"

        for name in collections:
            if name.startswith(old_prefix):
                new_name = new_prefix + name[len(old_prefix):]
                if new_name not in collections:
                    try:
                        client.update_collection_aliases(
                            change_aliases_operations=[
                                {"create_alias": {"collection_name": name, "alias_name": new_name}}
                            ]
                        )
                        log.info(f"Qdrant: aliased '{new_name}' -> '{name}'")
                    except Exception as e:
                        log.warning(f"Qdrant alias error for {name}: {e}")
    except ImportError:
        pass
    except Exception as e:
        log.warning(f"Qdrant prefix migration error (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Elasticsearch
# ---------------------------------------------------------------------------

def migrate_elasticsearch_prefixes():
    """Create index aliases from new prefix to old prefix collections."""
    try:
        from sage_is_ai.config import VECTOR_DB
        if VECTOR_DB != "elasticsearch":
            return

        from sage_is_ai.config import (
            ELASTICSEARCH_URL, ELASTICSEARCH_API_KEY,
            ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD,
            ELASTICSEARCH_CLOUD_ID, ELASTICSEARCH_CA_CERTS,
            SSL_ASSERT_FINGERPRINT, ELASTICSEARCH_INDEX_PREFIX,
        )
        from elasticsearch import Elasticsearch

        kwargs = {"request_timeout": 10}
        if ELASTICSEARCH_CLOUD_ID:
            kwargs["cloud_id"] = ELASTICSEARCH_CLOUD_ID
        else:
            kwargs["hosts"] = [ELASTICSEARCH_URL]
        if ELASTICSEARCH_API_KEY:
            kwargs["api_key"] = ELASTICSEARCH_API_KEY
        if ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD:
            kwargs["basic_auth"] = (ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD)
        if ELASTICSEARCH_CA_CERTS:
            kwargs["ca_certs"] = ELASTICSEARCH_CA_CERTS
        if SSL_ASSERT_FINGERPRINT:
            kwargs["ssl_assert_fingerprint"] = SSL_ASSERT_FINGERPRINT

        es = Elasticsearch(**kwargs)
        indices = list(es.indices.get(index="open_webui_collections*").keys())

        new_prefix = ELASTICSEARCH_INDEX_PREFIX  # "sage_is_ai_collections"
        old_prefix = "open_webui_collections"

        for idx_name in indices:
            new_name = new_prefix + idx_name[len(old_prefix):]
            try:
                es.indices.put_alias(index=idx_name, name=new_name)
                log.info(f"Elasticsearch: aliased '{new_name}' -> '{idx_name}'")
            except Exception as e:
                log.warning(f"Elasticsearch alias error for {idx_name}: {e}")
    except ImportError:
        pass
    except Exception as e:
        log.warning(f"Elasticsearch prefix migration error (non-fatal): {e}")


# ---------------------------------------------------------------------------
# OpenSearch
# ---------------------------------------------------------------------------

def migrate_opensearch_prefixes():
    """Create index aliases from new prefix to old prefix indices."""
    try:
        from sage_is_ai.config import VECTOR_DB
        if VECTOR_DB != "opensearch":
            return

        from sage_is_ai.config import (
            OPENSEARCH_URI, OPENSEARCH_SSL,
            OPENSEARCH_CERT_VERIFY, OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD,
        )
        from opensearchpy import OpenSearch

        client = OpenSearch(
            hosts=[OPENSEARCH_URI],
            use_ssl=OPENSEARCH_SSL,
            verify_certs=OPENSEARCH_CERT_VERIFY,
            http_auth=(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD),
        )

        indices = list(client.indices.get("open_webui*").keys())
        old_prefix = "open_webui"
        new_prefix = "sage_is_ai"

        for idx_name in indices:
            new_name = new_prefix + idx_name[len(old_prefix):]
            try:
                client.indices.put_alias(index=idx_name, name=new_name)
                log.info(f"OpenSearch: aliased '{new_name}' -> '{idx_name}'")
            except Exception as e:
                log.warning(f"OpenSearch alias error for {idx_name}: {e}")
    except ImportError:
        pass
    except Exception as e:
        log.warning(f"OpenSearch prefix migration error (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Milvus
# ---------------------------------------------------------------------------

def migrate_milvus_prefixes():
    """Rename Milvus collections from old prefix to new prefix."""
    try:
        from sage_is_ai.config import VECTOR_DB
        if VECTOR_DB != "milvus":
            return

        from sage_is_ai.config import MILVUS_URI
        from pymilvus import MilvusClient as Client

        client = Client(uri=MILVUS_URI)
        collections = client.list_collections()

        old_prefix = "open_webui"
        new_prefix = "sage_is_ai"

        for name in collections:
            if name.startswith(old_prefix):
                new_name = new_prefix + name[len(old_prefix):]
                if new_name not in collections:
                    try:
                        client.rename_collection(old_name=name, new_name=new_name)
                        log.info(f"Milvus: renamed '{name}' -> '{new_name}'")
                    except Exception as e:
                        log.warning(f"Milvus rename error for {name}: {e}")
    except ImportError:
        pass
    except Exception as e:
        log.warning(f"Milvus prefix migration error (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Pinecone
# ---------------------------------------------------------------------------

def migrate_pinecone_prefixes():
    """Log a warning — Pinecone has no rename/alias API."""
    try:
        from sage_is_ai.config import VECTOR_DB
        if VECTOR_DB != "pinecone":
            return

        log.warning(
            "Pinecone prefix migration: Pinecone does not support index renaming. "
            "If you were using the old 'open-webui-index' name, you must manually "
            "recreate your index as 'sage-is-ai-index' or set PINECONE_INDEX_NAME "
            "to your existing index name."
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def run_prefix_migrations(app) -> None:
    """
    Run all applicable prefix migrations.  Called once during app startup.
    All migrations are non-fatal — errors are logged but don't block startup.
    """
    log.info("Running service prefix migrations (open-webui -> sage-is-ai)...")

    # Redis (async)
    redis_client = getattr(app.state, "redis", None)
    await migrate_redis_prefixes(redis_client)

    # Vector DBs (sync — fast enough for startup)
    migrate_qdrant_prefixes()
    migrate_elasticsearch_prefixes()
    migrate_opensearch_prefixes()
    migrate_milvus_prefixes()
    migrate_pinecone_prefixes()

    log.info("Service prefix migrations complete.")
