# 🧩 Domain-Driven Design & Separation of Concerns

This section explains how **Domain-Driven Design (DDD)**, **Hexagonal Architecture**, and strict **Separation of Concerns** are applied in this project.  
It also covers how these principles make the system **evolvable**, **low-coupled**, and ready to split into **microservices** when needed.

---

## 1) Bounded Contexts

The system is organized into **three main bounded contexts**:

| Context    | Purpose                                               | Examples of Responsibilities                                  |
|------------|-------------------------------------------------------|----------------------------------------------------------------|
| **Users**  | Authentication, authorization, and RBAC               | Managing `User`, `Role`, issuing tokens                       |
| **Content** (CMS) | Editorial management of programs & media           | CRUD for `Content` & `ContentMedia`, imports from providers   |
| **Discovery** | Search, browse, and public content discovery       | OpenSearch queries, CMS hydration via read port               |

**Rules:**
- No context directly accesses another’s database or repositories.
- Shared types are **published** in `shared/entities`, these are stable DTOs used for read models.
- Any cross-context call goes through a **port**.

---

## 2) Ports & Adapters (Hexagonal Application)

Within each context:

- **Ports** define contracts for inbound (offered to others) and outbound (needed from others) interactions.
- **Adapters** implement those ports, binding the domain to actual infrastructure or other contexts.

Example from CMS:
- **Outbound ports**: `IndexerPort`, `CachePort`, `ExternalMediaProviderPort`
- **Outbound adapters**: `OpenSearchIndexer`, `RedisCacheAdapter`, `YouTubeProvider`
- **Inbound port**: `ReadPort` (Discovery reads content through this)

---

## 3) Package-Level Separation of Concerns

Each top-level package has **clear roles**:
- content/ `#The CMS bounded context`
- domain/ `#Entities, models, repositories (pure domain)`
- services/ `#Application services (use cases)`
- ports/ `#Port definitions (interfaces)`
- adapters/ `#Port implementations (infra, integration)`
- routers/ `#HTTP API layer`
- tasks/ `#Async background jobs`


Similar patterns apply to `users/` and `discovery/`.

---

## 4) How We Keep Low Coupling

- **Domain layer**: Contains no references to FastAPI, SQLAlchemy sessions, Redis clients, or OpenSearch clients.
- **Service layer**: Talks to **ports**, not concrete implementations.
- **Adapters**: Encapsulate all infrastructure code and can be swapped without changing the service.
- **Routers**: Only orchestrate dependencies and invoke services — no business logic.

---

## 5) Why `shared/entities` Exists

- Acts as **published contracts** between contexts.
- Ensures changes in CMS internal models do not break Discovery.
- Allows versioning: `ContentOutV1`, `ContentOutV2` can coexist.
- Keeps read models immutable — services produce them, but no code mutates them downstream.

---

## 6) Modular Monolith vs Microservices

### Modular Monolith (current)
- All code lives in one repo, one deployment.
- Ports connect modules **in-process** (e.g., `InProcessReadAdapter`).
- Easy to refactor, debug, and test end-to-end.

### Microservices (future option)
- Replace in-process adapters with HTTP or gRPC clients.
- Each bounded context becomes its own service with its own DB.
- Use the same ports/interfaces — no change in the domain layer.
- `shared/entities` becomes a separate versioned package or schema definition repo.
- Async events (via Kafka, RabbitMQ) can be introduced for cache/index updates.

---

## 7) Extension Paths

- **Add new outbound integrations**: Implement a new adapter for an existing port (e.g., `VimeoProvider` for `ExternalMediaProviderPort`).
- **Swap infrastructure**: Replace `RedisCacheAdapter` with a Memcached adapter without touching services.
- **Add new contexts**: Create a new top-level package with its own ports, services, and adapters — integrate only via ports.

---

## 8) Benefits of This Approach

- **Isolation**: Bugs in one context have minimal impact on others.
- **Testability**: Mock ports for unit tests; real adapters for integration tests.
- **Flexibility**: Swap infra/services with minimal code changes.
- **Scalability**: Can grow as a monolith or be split into microservices naturally.

---

## 9) Key Takeaways

- **DDD + Hexagonal** forces us to be explicit about dependencies.
- **Low coupling** means safer, faster changes.
- **Separation of Concerns** lets us move between architectural styles without rewriting core logic.

---

## 💡 Read Next
1. [Overview](00-Overview.md)
2. [Architecture](01-Architecture.md)
3. [Design Philosophy](02-Design-Philosophy.md)
4. DDD & Separation of Concerns 👈🏼
5. [API Documentation](04-API-Documentation.md)
6. [Business Flows](05-Business-Flows.md)
7. [Deployment Guide](06-Deployment.md)
8. [Future Work](07-Future-Work.md)