# 🖥️ Deployment & Local Development

This guide shows how to run the project **locally** (Poetry + native services) and **via Docker Compose** (Postgres, Redis, OpenSearch, API, Celery worker).

---

## 1) Prerequisites

- **Python 3.12**
- **Poetry** (recommended)  
  ```bash
  pip install poetry
  ```
- Docker + Docker Compose (for containerized run)

## 2) Run with Docker Compose (Recommended)

We assume you have the repo in your machine.
Go ahead and run the following command

```bash
docker-compose up --build
```

### This will:
- Start Postgres, Redis, and OpenSearch.
- Run Alembic migrations inside app.
- Launch FastAPI on http://localhost:8000.
- Launch a Celery worker that handles indexing jobs, etc.

### Health Checks
- API Docs (Swagger): http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc
- OpenSearch (basic ping): curl http://localhost:9200
- Postgres: container logs show readiness
- Redis: docker exec -it <redis-container> redis-cli ping → PONG

---

## 3) Troubleshooting
### 3.1 OpenSearch container fails with:
No custom admin password found. Please provide a password via OPENSEARCH_INITIAL_ADMIN_PASSWORD

Ensure .env has:
```bash 
OPENSEARCH_INITIAL_ADMIN_PASSWORD=admin123
```


And the compose service uses:
```yaml
environment:
  - discovery.type=single-node
  - plugins.security.disabled=true
  - OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
  - OPENSEARCH_INITIAL_ADMIN_PASSWORD=${OS_PASSWORD}
```

### 3.2 Celery worker can’t connect to Redis (Connection refused)

In Docker, broker URL must target the service name redis, not localhost:
```bash
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```


### 3.3 API container can’t connect to Postgres (Connect call failed … 127.0.0.1:5432)

Inside Docker, use `DB_HOST=db` and `DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/cms`.

- Ensure the database exists with our compose, it’s created automatically via env vars.
- Check logs: `docker-compose logs db`

### 3.4 Alembic errors about existing tables (DuplicateTableError)

The database already has tables. If it’s a dev environment, you can reset:
```bash
docker-compose down -v   # removes volumes
docker-compose up --build
```

Otherwise, inspect alembic_version table and your migration history.

You are all set 🎉

---

## 💡 Read Next
1. [Overview](00-Overview.md)
2. [Architecture](01-Architecture.md)
3. [Design Philosophy](02-Design-Philosophy.md)
4. [DDD & Separation of Concerns](03-DDD-and-Separation-of-Concerns.md)
5. [API Documentation](04-API-Documentation.md) 
6. [Business Flows](05-Business-Flows.md)
7. Deployment Guide 👈🏼
 