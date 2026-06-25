"""
Infrastructure connectivity checks on startup.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ServiceStatus:
    name: str
    healthy: bool
    latency_ms: float = 0.0
    error: str | None = None


@dataclass
class InfrastructureStatus:
    services: list[ServiceStatus] = field(default_factory=list)
    all_healthy: bool = True


async def _check_postgres() -> ServiceStatus:
    """Check PostgreSQL connectivity."""
    from app.db.database import check_database_health
    t0 = __import__("time").time()
    try:
        result = await check_database_health()
        latency = round((__import__("time").time() - t0) * 1000, 2)
        return ServiceStatus(
            name="PostgreSQL",
            healthy=result["status"] == "connected",
            latency_ms=latency,
            error=result.get("error"),
        )
    except Exception as e:
        return ServiceStatus(name="PostgreSQL", healthy=False, error=str(e))


async def _check_redis() -> ServiceStatus:
    """Check Redis connectivity."""
    t0 = __import__("time").time()
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings

        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        return ServiceStatus(
            name="Redis",
            healthy=True,
            latency_ms=round((__import__("time").time() - t0) * 1000, 2),
        )
    except Exception as e:
        return ServiceStatus(name="Redis", healthy=False, error=str(e))


async def _check_elasticsearch() -> ServiceStatus:
    """Check Elasticsearch connectivity."""
    t0 = __import__("time").time()
    try:
        from elasticsearch import AsyncElasticsearch
        from app.core.config import settings

        es = AsyncElasticsearch(
            settings.elasticsearch_url,
            request_timeout=5,
            node_class=None,
        )
        await es.cluster.health(wait_for_status="yellow")
        await es.close()
        return ServiceStatus(
            name="Elasticsearch",
            healthy=True,
            latency_ms=round((__import__("time").time() - t0) * 1000, 2),
        )
    except Exception as e:
        return ServiceStatus(name="Elasticsearch", healthy=False, error=str(e))


async def _check_minio() -> ServiceStatus:
    """Check MinIO connectivity."""
    t0 = __import__("time").time()
    try:
        from minio import Minio
        from app.core.config import settings

        client = Minio(
            settings.minio_url,
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=False,
        )
        client.list_buckets()
        latency = round((__import__("time").time() - t0) * 1000, 2)
        return ServiceStatus(
            name="MinIO",
            healthy=True,
            latency_ms=latency,
        )
    except Exception as e:
        return ServiceStatus(name="MinIO", healthy=False, error=str(e))


async def run_health_checks() -> InfrastructureStatus:
    """Run all infrastructure health checks concurrently."""
    results = await asyncio.gather(
        _check_postgres(),
        _check_redis(),
        _check_elasticsearch(),
        _check_minio(),
        return_exceptions=True,
    )

    services: list[ServiceStatus] = []
    all_healthy = True
    for r in results:
        if isinstance(r, Exception):
            svc = ServiceStatus(name="Unknown", healthy=False, error=str(r))
            all_healthy = False
        else:
            svc = r
            if not svc.healthy:
                all_healthy = False
        services.append(svc)

    return InfrastructureStatus(services=services, all_healthy=all_healthy)
