# URL Shortener Microservice

A high-performance URL shortening microservice built with FastAPI, PostgreSQL, and Redis.

## Features

- **URL Shortening**: Create short URLs (7-character base62 IDs)
- **Fast Redirects**: Redis-cached redirects with <50ms p99 latency
- **Click Statistics**: Track and retrieve click counts
- **URL Deletion**: Soft delete with cache cleanup
- **Rate Limiting**: Redis-based sliding window rate limiting (100 req/min per IP)
- **SSRF Protection**: Blocks requests to private/internal IPs
- **Health Checks**: Monitors database and Redis connectivity
- **Graceful Shutdown**: Proper connection cleanup on SIGTERM/SIGINT

## Tech Stack

- **Python 3.11+** with async/await
- **FastAPI** for REST API with auto-generated OpenAPI docs
- **SQLAlchemy 2.0** (async) with PostgreSQL 15
- **Redis 7** for caching and rate limiting
- **Alembic** for database migrations
- **Docker** and docker-compose for containerization

## Quick Start

### Prerequisites

- Docker and docker-compose
- Python 3.11+ (for local development)

### Using Docker