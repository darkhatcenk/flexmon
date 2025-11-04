"""
Elasticsearch client and utilities
"""
from elasticsearch import AsyncElasticsearch
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import logging
from ..config import settings

logger = logging.getLogger(__name__)

# Global ES client
_es_client: Optional[AsyncElasticsearch] = None


async def init_es():
    """Initialize Elasticsearch client"""
    global _es_client

    # Force ES v8 compatibility headers
    default_headers = {
        "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
        "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8",
    }

    _es_client = AsyncElasticsearch(
        [settings.elasticsearch_url],
        basic_auth=(settings.elasticsearch_user, settings.elasticsearch_password),
        verify_certs=False,
        request_timeout=30,
        headers=default_headers
    )

    # Test connection
    await _es_client.cluster.health()
    logger.info("Elasticsearch client initialized with v8 compatibility")


async def close_es():
    """Close Elasticsearch client"""
    global _es_client
    if _es_client:
        await _es_client.close()
        logger.info("Elasticsearch client closed")


async def get_cluster_health() -> Dict[str, Any]:
    """Get cluster health"""
    return await _es_client.cluster.health()


async def load_templates_and_ilm():
    """Load index templates and ILM policies"""
    templates_dir = Path(__file__).parent.parent / "models" / "es_index_templates"

    # Load ILM policy
    ilm_path = templates_dir / "ilm-policy.json"
    if ilm_path.exists():
        with open(ilm_path) as f:
            ilm_policy = json.load(f)

        try:
            await _es_client.ilm.put_lifecycle(
                name="flexmon-logs-ilm",
                body=ilm_policy
            )
            logger.info("ILM policy loaded: flexmon-logs-ilm")
        except Exception as e:
            logger.warning(f"Failed to load ILM policy: {e}")

    # Load index templates
    for template_file in ["logs-template.json", "platform-logs-template.json"]:
        template_path = templates_dir / template_file
        if template_path.exists():
            with open(template_path) as f:
                template = json.load(f)

            template_name = template_file.replace("-template.json", "")

            try:
                await _es_client.indices.put_index_template(
                    name=template_name,
                    body=template
                )
                logger.info(f"Index template loaded: {template_name}")
            except Exception as e:
                logger.warning(f"Failed to load template {template_name}: {e}")


async def index_log(index: str, document: Dict[str, Any]) -> Dict[str, Any]:
    """Index a single log document"""
    return await _es_client.index(
        index=index,
        document=document
    )


async def bulk_index_logs(index: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Bulk index log documents"""
    body = []
    for doc in documents:
        body.append({"index": {"_index": index}})
        body.append(doc)

    return await _es_client.bulk(body=body)


async def search_logs(
    index: str,
    query: Dict[str, Any],
    size: int = 100,
    from_: int = 0,
    sort: Optional[List] = None
) -> Dict[str, Any]:
    """Search logs"""
    return await _es_client.search(
        index=index,
        query=query,
        size=size,
        from_=from_,
        sort=sort or [{"@timestamp": {"order": "desc"}}]
    )


async def count_logs(index: str, query: Dict[str, Any]) -> int:
    """Count logs matching query"""
    result = await _es_client.count(index=index, query=query)
    return result["count"]
