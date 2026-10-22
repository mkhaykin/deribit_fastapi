import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Generator

import asyncpg
import httpx2
import psycopg2
import pytest
import pytest_asyncio
from fastapi import FastAPI
from redis.asyncio import Redis
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer

from api.routers.health import router as health_router
from api.routers.price import router as price_router
from config import config


@pytest.fixture(scope="session")
def postgres_url() -> Generator[str, None, None]:
    with PostgresContainer("postgres:15.1-alpine") as postgres:
        url = postgres.get_connection_url()
        url = url.replace(
            "postgresql+psycopg2://",
            "postgresql://",
        )
        yield url


@pytest.fixture(scope="session")
def redis_url() -> Generator[str, None, None]:
    with RedisContainer("redis:7.2-alpine") as redis:
        host = redis.get_container_host_ip()
        port = redis.get_exposed_port(6379)
        yield f"redis://{host}:{port}/0"


@pytest_asyncio.fixture
async def pg_pool(postgres_url: str) -> AsyncIterator[asyncpg.Pool]:
    pool = await asyncpg.create_pool(
        dsn=postgres_url,
        min_size=1,
        max_size=5,
    )

    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS index_prices (
                id BIGSERIAL PRIMARY KEY,
                ticker TEXT NOT NULL,
                price NUMERIC NOT NULL,
                timestamp BIGINT NOT NULL
            )
        """)

    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE index_prices RESTART IDENTITY")

    try:
        yield pool
    finally:
        await pool.close()


@pytest_asyncio.fixture
async def redis_client(redis_url: str) -> AsyncIterator[Redis]:
    redis = Redis.from_url(redis_url, decode_responses=True)
    await redis.flushdb()
    try:
        yield redis
    finally:
        await redis.aclose()


@pytest.fixture
def api_app(postgres_url: str, redis_url: str) -> Generator[FastAPI, None, None]:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pool = await asyncpg.create_pool(
            dsn=postgres_url,
            min_size=1,
            max_size=5,
        )
        app.state.redis = Redis.from_url(
            redis_url,
            decode_responses=True,
        )

        async with app.state.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS index_prices (
                    id BIGSERIAL PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    price NUMERIC NOT NULL,
                    timestamp BIGINT NOT NULL
                )
            """)
            await conn.execute("TRUNCATE TABLE index_prices RESTART IDENTITY")

        await app.state.redis.flushdb()

        try:
            yield
        finally:
            await app.state.redis.aclose()
            await app.state.pool.close()

    app = FastAPI(lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(price_router, prefix="/api/v1")

    yield app


@pytest_asyncio.fixture
async def api_client(api_app: FastAPI):
    async with api_app.router.lifespan_context(api_app):
        transport = httpx2.ASGITransport(app=api_app)

        async with httpx2.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            yield client


@pytest.fixture
def pg_sync_conn(postgres_url: str) -> Generator[psycopg2.extensions.connection, None, None]:
    # подменяем dsn в глобальном конфиге для тестируемой функции store_prices
    # TODO вообще в функцию передавать dsn, но пока так
    config.DATABASE_DSN = postgres_url

    with psycopg2.connect(dsn=postgres_url) as conn:
        with conn.cursor() as cur:
            # таблица: TODO очень много где встречается, поправить при случае
            cur.execute("""
                CREATE TABLE IF NOT EXISTS index_prices (
                    id BIGSERIAL PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    price NUMERIC NOT NULL,
                    timestamp BIGINT NOT NULL
                )
            """)
            # очистка, сброс счетчика
            cur.execute("TRUNCATE TABLE index_prices RESTART IDENTITY")
        conn.commit()

        # Передаем коннект в тест
        yield conn


@pytest.fixture(scope="session", autouse=True)
def quiet_testcontainers_teardown():
    """подавляем логи urllib3/docker во время уничтожения контейнеров"""
    yield
    # вроде только они шумят, но проверить
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)
    logging.getLogger("docker").setLevel(logging.CRITICAL)
