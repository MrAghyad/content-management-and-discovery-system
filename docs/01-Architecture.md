# 🏛 Architecture

## 1. Overview

The system is structured as a **modular monolith** following **Domain-Driven Design (DDD)** principles.  
The modules are **loosely coupled** and communicate via **well-defined interfaces** (ports/adapters).

The separation of concerns makes it easy to:
- Maintain and scale as a single application.
- Transition to **microservices** with minimal changes.

---

## 2. Core Modules
### app/
- core/ → Config, security, database session, caching, Celery tasks.
- main.py → Entry point for FastAPI application.

### users/
- Domain: User and Role.
- Authentication via JWT.
- Role-based access control.
- Services: AuthService, UserService, RoleService.
- Repositories
- Routers: /v1/auth, /v1/users, /v1/roles.

### content/
- Domain: Content and Media.
- Services: Create, update, delete, content, assign categories, attach media.
- Repositories
- Adapters:
  - OpenSearchIndexer for indexing.
  - RedisCacheAdapter for caching.
  - External provider adapters (e.g., YouTubeProvider).
- Routers: /v1/contents, /v1/import, /v1/contents/{id}/media.

### discovery/

- Searches indexed content in OpenSearch.
- Hydrates content metadata from CMS via cache.
- Public API: /v1/discovery/search, /v1/discovery/contents/{id}.

### shared/
- DTOs / Pydantic models shared between modules.
- Avoids circular dependencies.

---

## 3. Interactions & Data Flow
Example: Creating Content
- Request → POST /v1/contents
- Router → ContentService.create()
- Repository → Insert metadata into PostgreSQL.
- Indexer → Send content data to OpenSearch.
- Cache → Store content in Redis for fast retrieval.
- Response → Return ContentOut.

Example: Searching Content
- Request → GET /v1/discovery/search?q=example
- DiscoveryService → Query OpenSearch.
- Hydration → Fetch metadata from CMS via CachePort.
- Response → Paginated list of ContentOut.

--- 

## 4. Ports & Adapters Pattern

We use ports and adapters to isolate domain logic from infrastructure:
- Ports: Abstract interfaces (IndexerPort, CachePort, ExternalMediaProviderPort).
- Adapters: Implementations (OpenSearchIndexer, RedisCacheAdapter, YouTubeProvider).
This ensures minimal coupling between the domain and external systems.

---

## 5. Benefits of Current Design
✅ Low coupling between modules.<br>
✅ Easy to test (mock ports).<br>
✅ Flexible, where you can swap adapters without affecting domain logic.<br>
✅ Ready for microservices split.

---

## 6. Microservices Readiness

Because each module has:
- Its own domain models
- Clear service boundaries
- Dependency injection for infrastructure

… we can split them into services like:

- User Service → Auth, roles.
- Content Service → CMS operations & Import flowss.
- Search Service → OpenSearch & Discovery.

This can be done incrementally by replacing direct service calls with API calls between services.


---
## 💡 Read Next
1. [Overview](00-Overview.md)
2. Architecture 👈🏼
3. [Design Philosophy](02-Design-Philosophy.md)
4. [DDD & Separation of Concerns](03-DDD-and-Separation-of-Concerns.md)
5. [API Documentation](04-API-Documentation.md)
6. [Business Flows](05-Business-Flows.md)
7. [Deployment Guide](06-Deployment.md)
8. [Future Work](07-Future-Work.md)