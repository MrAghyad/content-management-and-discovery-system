# 🎬 Modular CMS & Discovery Platform

This repository contains a **FastAPI-based modular monolith** implementing:
- **CMS** (content + media management)
- **Discovery** (search & browse)
- **User management** (auth, roles, permissions)
- **Importers** (e.g., YouTube, extensible for others)
- **Indexing & caching** (OpenSearch + Redis)

## 📚 Documentation

We keep our documentation organized into separate pages for clarity.

1. [Overview](docs/00-Overview.md)
2. [Architecture](docs/01-Architecture.md)
3. [Design Philosophy](docs/02-Design-Philosophy.md)
4. [DDD & Separation of Concerns](docs/03-DDD-and-Separation-of-Concerns.md)
5. [API Documentation](docs/04-API-Documentation.md)
6. [Business Flows](docs/05-Business-Flows.md)
7. [Deployment Guide](docs/06-Deployment.md)

---

## 🚀 Quick Start

```bash
docker-compose up --build
```

---

## **[00-Overview](docs/00-Overview.md)**

Contains:
- High-level project description
- Main features
- Core components (CMS, Discovery, Users)
- Tech stack
- Data flow at a glance

---

## **[01-Architecture](docs/01-Architecture.md)**

Contains:
- Data flow diagram
- Explanation of **bounded contexts**
- How **ports & adapters** are used
- How **services, repositories, entities, and routers** interact

---

## **[02-Design-Philosophy](docs/02-Design-Philosophy.md)**

Contains:
- SOLID principles in practice
- Low coupling through ports/adapters
- DTOs in `shared/` as a published language

---

## **[03-DDD-and-Separation-of-Concerns](docs/03-DDD-and-Separation-of-Concerns.md)**

Contains:
- Context boundaries
- Folder/package relationships
- How low coupling is enforced
- How services depend only on ports, not adapters

---

## **[04-API-Documentation](docs/04-API-Documentation.md)**

Contains:
- **All routers** with:
  - Endpoint summaries
  - Request/response examples
  - Query/body param explanations
  - Auth requirements
---

## **[05-Business-Flows.md](docs/05-Business-Flows.md)**

Contains:
- **Content lifecycle**: create → update → delete → index → cache
- **Media lifecycle**
- **Search & discovery flow**
- **User/role creation & auth flow**
- **Import flow** (YouTube → CMS)
- Diagram for each

---

## **[06-Deployment](docs/06-Deployment.md)**

Contains:
- docker-compose setup (all services on same network)
- Troubleshooting guide


