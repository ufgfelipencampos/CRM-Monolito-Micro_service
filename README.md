# CRM Backend

Backend de CRM desenvolvido como **monolito com organização orientada a domínios**, projetado para migração incremental a microserviços.

**Stack:** Python 3.12 · FastAPI · PostgreSQL 16 · SQLAlchemy 2 (async) · Alembic · Docker · uv

---

## Índice

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Módulos MVP](#módulos-mvp)
- [Pré-requisitos](#pré-requisitos)
- [Quick Start](#quick-start)
- [Desenvolvimento Local](#desenvolvimento-local)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [API e Documentação](#api-e-documentação)
- [Banco de Dados](#banco-de-dados)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Credenciais Padrão](#credenciais-padrão)
- [Roadmap](#roadmap)

---

## Visão Geral

Sistema de CRM focado em gestão de vendas B2B. O MVP cobre o ciclo completo de vendas: autenticação com controle de acesso por papéis (RBAC), gestão de contatos e contas (empresas), pipeline de oportunidades com visualização Kanban e auditoria de todas as operações críticas.

---

## Arquitetura

```
app/
├── core/          ← Infraestrutura transversal (config, DB, JWT, deps)
├── shared/        ← Utilitários compartilhados (paginação, base models)
└── modules/
    ├── auth/          ← Domínio: autenticação e controle de acesso
    ├── contacts/      ← Domínio: contatos (pessoas físicas / leads)
    ├── accounts/      ← Domínio: contas (empresas)
    ├── opportunities/ ← Domínio: oportunidades e pipeline de vendas
    └── audit/         ← Domínio: auditoria e rastreabilidade
```

Cada módulo segue a mesma estrutura interna:

```
módulo/
├── models.py    ← Entidades SQLAlchemy (ORM)
├── schemas.py   ← Contratos Pydantic (request/response)
├── service.py   ← Regras de negócio e acesso a dados
└── router.py    ← Endpoints FastAPI
```

Essa separação permite que qualquer módulo seja extraído como microserviço independente sem reescrever a lógica de negócio.

---

## Módulos MVP

| Módulo | Histórias | Endpoints principais |
|---|---|---|
| **Autenticação** (AUT) | AUT-001, AUT-002, AUT-003 | `/auth/*`, `/admin/users`, `/admin/roles` |
| **Contatos** (CON) | CON-001, CON-002, CON-003 | `/contacts` |
| **Contas** (ACC) | ACC-001, ACC-002 | `/accounts`, `/accounts/{id}/hierarchy` |
| **Oportunidades** (OPP) | OPP-001 a OPP-004 | `/opportunities`, `/pipeline`, `/pipeline/stages` |
| **Auditoria** (NFR) | NFR-003 | `/audit` |

---

## Pré-requisitos

| Ferramenta | Versão mínima | Uso |
|---|---|---|
| [Docker](https://docs.docker.com/get-docker/) | 24+ | Containers |
| [Docker Compose](https://docs.docker.com/compose/) | 2.20+ | Orquestração |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | 0.5+ | Gerenciamento de pacotes Python (dev local) |

> Para desenvolvimento local **fora do Docker**, Python 3.12+ também é necessário.

---

## Quick Start

```bash
# 1. Clone e entre no diretório
git clone <repo-url>
cd CRM-Monolito-Micro_service

# 2. Configure o ambiente
cp .env.example .env
# Edite .env se necessário — os valores padrão já funcionam para desenvolvimento

# 3. Suba os containers (usa o override de dev automaticamente)
docker compose up --build
```

A API estará disponível em `http://localhost:8000/api/v1/docs`.

---

## Desenvolvimento Local

### Como funciona o override

O arquivo `docker-compose.override.yml` é carregado **automaticamente** pelo Docker Compose sempre que estiver no mesmo diretório que `docker-compose.yml`. Não é necessário nenhuma flag extra.

```bash
# Equivalente completo (ambos os arquivos são mesclados)
docker compose -f docker-compose.yml -f docker-compose.override.yml up
```

### Comandos do dia a dia

```bash
# Iniciar tudo (primeira vez: adicione --build)
docker compose up --build

# Iniciar em background
docker compose up -d

# Ver logs da aplicação em tempo real
docker compose logs -f app

# Parar tudo
docker compose down

# Parar e remover volumes (reset completo do banco)
docker compose down -v
```

### Serviços em desenvolvimento

| Serviço | URL | Descrição |
|---|---|---|
| API | `http://localhost:8000` | FastAPI com hot reload |
| Swagger UI | `http://localhost:8000/api/v1/docs` | Documentação interativa |
| ReDoc | `http://localhost:8000/api/v1/redoc` | Documentação alternativa |
| pgAdmin | `http://localhost:5050` | Interface web do PostgreSQL |
| Mailpit (SMTP) | `http://localhost:8025` | Inspecionar e-mails enviados |
| PostgreSQL | `localhost:5432` | Conexão direta (TablePlus, DBeaver, etc.) |

### Migrações

```bash
# Aplicar todas as migrações pendentes
docker compose exec app alembic upgrade head

# Gerar nova migração após alterar um model
docker compose exec app alembic revision --autogenerate -m "descricao"

# Reverter a última migração
docker compose exec app alembic downgrade -1

# Ver histórico
docker compose exec app alembic history --verbose
```

### Gerenciamento de dependências (uv)

```bash
# Instalar todas as dependências (incluindo dev)
uv sync --extra dev

# Adicionar nova dependência de produção
uv add fastapi-pagination

# Adicionar dependência apenas de desenvolvimento
uv add --dev pytest-factory-boy

# Atualizar dependências
uv lock --upgrade
```

### Testes

```bash
# Dentro do container
docker compose exec app uv run pytest -v

# Localmente (com uv instalado)
uv run pytest -v

# Com cobertura de código
uv run pytest --cov=app --cov-report=html
```

### Rodar sem Docker (dev puro)

Necessário: Python 3.12+, PostgreSQL rodando localmente ou via container.

```bash
# 1. Ajuste POSTGRES_HOST=localhost no .env

# 2. Instale as dependências
uv sync

# 3. Execute as migrações
uv run alembic upgrade head

# 4. Inicie a aplicação
uv run uvicorn app.main:app --reload --port 8000
```

---

## Variáveis de Ambiente

Copie `.env.example` para `.env`. O arquivo `.env` **nunca deve ser commitado** (já está no `.gitignore`).

| Variável | Padrão (dev) | Descrição |
|---|---|---|
| `SECRET_KEY` | `dev-secret-...` | Chave para assinar tokens JWT — **obrigatório trocar em produção** |
| `ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Validade do access token em minutos |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Validade do refresh token em dias |
| `POSTGRES_HOST` | `db` | Host do PostgreSQL (`db` no Docker, `localhost` fora) |
| `POSTGRES_PORT` | `5432` | Porta do PostgreSQL |
| `POSTGRES_DB` | `crm_db` | Nome do banco de dados |
| `POSTGRES_USER` | `crm_user` | Usuário do banco |
| `POSTGRES_PASSWORD` | `crm_strong_pass_2024` | Senha do banco — **obrigatório trocar em produção** |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Origens CORS permitidas (JSON array) |
| `DEBUG` | `true` | Habilita logs SQL e detalhes de erro |
| `SESSION_INACTIVITY_MINUTES` | `60` | Tempo de inatividade para expirar sessão |
| `PASSWORD_RESET_RATE_LIMIT_MINUTES` | `15` | Janela de tempo para tentativas de reset |
| `AUDIT_LOG_RETENTION_DAYS` | `365` | Retenção dos logs de auditoria |

---

## API e Documentação

### Autenticação

A API usa **Bearer Token (JWT)**. O endpoint de login segue o padrão OAuth2 com `form-data`:

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -F "username=admin@crm.local" \
  -F "password=Admin@1234"

# Resposta
# { "access_token": "...", "refresh_token": "...", "token_type": "bearer" }

# Usar o token
curl http://localhost:8000/api/v1/contacts \
  -H "Authorization: Bearer <access_token>"

# Renovar token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

### Mapa de endpoints

```
Autenticação
  POST  /api/v1/auth/login
  POST  /api/v1/auth/refresh
  POST  /api/v1/auth/forgot-password
  POST  /api/v1/auth/reset-password
  GET   /api/v1/auth/me
  POST  /api/v1/auth/change-password

Usuários  (requer papel: admin)
  GET   /api/v1/admin/users
  POST  /api/v1/admin/users
  GET   /api/v1/admin/users/{id}
  PUT   /api/v1/admin/users/{id}
  DELETE /api/v1/admin/users/{id}

Papéis  (requer papel: admin)
  GET   /api/v1/admin/roles
  POST  /api/v1/admin/roles
  GET   /api/v1/admin/roles/{id}
  PUT   /api/v1/admin/roles/{id}
  DELETE /api/v1/admin/roles/{id}

Contatos  (requer papel: seller+)
  GET   /api/v1/contacts          ?name= &email= &lead_source= &tag= &is_active= &owner_id= &page= &per_page=
  POST  /api/v1/contacts
  GET   /api/v1/contacts/{id}
  PUT   /api/v1/contacts/{id}
  DELETE /api/v1/contacts/{id}    soft delete — inativa o registro

Contas  (requer papel: seller+)
  GET   /api/v1/accounts          ?name= &cnpj= &segment= &is_active= &owner_id= &page= &per_page=
  POST  /api/v1/accounts
  GET   /api/v1/accounts/{id}
  PUT   /api/v1/accounts/{id}
  DELETE /api/v1/accounts/{id}    soft delete
  GET   /api/v1/accounts/{id}/hierarchy

Pipeline — estágios  (leitura: todos | escrita: admin)
  GET   /api/v1/pipeline/stages
  POST  /api/v1/pipeline/stages
  PUT   /api/v1/pipeline/stages/{id}

Pipeline — visão Kanban  (requer papel: seller+)
  GET   /api/v1/pipeline          ?owner_id=

Oportunidades  (requer papel: seller+)
  GET   /api/v1/opportunities     ?title= &stage_id= &status= &owner_id= &contact_id= &account_id= &page= &per_page=
  POST  /api/v1/opportunities
  GET   /api/v1/opportunities/{id}
  PUT   /api/v1/opportunities/{id}
  PATCH /api/v1/opportunities/{id}/stage   { "stage_id": "uuid" }
  PATCH /api/v1/opportunities/{id}/close   { "status": "won|lost", "lost_reason": "..." }

Auditoria  (requer papel: admin | manager)
  GET   /api/v1/audit             ?entity_type= &entity_id= &action= &user_id= &from_date= &to_date= &page= &per_page=

Health
  GET   /health
  GET   /api/v1/health
```

---

## Banco de Dados

O diagrama ERD completo está em [`Docs/database_uml.md`](Docs/database_uml.md).

### Resumo das tabelas

| Tabela | Domínio | Descrição |
|---|---|---|
| `users` | auth | Usuários do sistema |
| `roles` | auth | Papéis de acesso |
| `permissions` | auth | Permissões por módulo para cada papel |
| `user_roles` | auth | Associação N:N usuário ↔ papel |
| `password_reset_tokens` | auth | Tokens temporários para recuperação de senha |
| `contacts` | contacts | Pessoas físicas / prospects |
| `accounts` | accounts | Empresas com suporte a hierarquia matriz/filial |
| `contact_accounts` | shared | Associação N:N contatos ↔ contas |
| `pipeline_stages` | opportunities | Estágios configuráveis do funil |
| `opportunities` | opportunities | Oportunidades de venda |
| `audit_logs` | audit | Registro imutável de operações críticas |

### Papéis criados automaticamente no startup

| Papel | Acesso |
|---|---|
| `admin` | Total — todos os módulos |
| `manager` | Leitura e escrita em vendas; leitura em admin e auditoria |
| `seller` | Gerencia contatos, contas e oportunidades próprios |
| `viewer` | Somente leitura em todos os módulos |

---

## Estrutura do Projeto

```
CRM-Monolito-Micro_service/
├── .env                          ← Variáveis de ambiente (não commitado)
├── .env.example                  ← Template das variáveis
├── .gitignore
├── Dockerfile                    ← Imagem de produção
├── docker-compose.yml            ← Compose base
├── docker-compose.override.yml   ← Overrides para desenvolvimento local
├── pyproject.toml                ← Dependências gerenciadas pelo uv
├── uv.lock                       ← Lock file (gerado pelo uv sync)
├── alembic.ini                   ← Configuração do Alembic
├── alembic/
│   ├── env.py                    ← Ambiente async das migrações
│   ├── script.py.mako            ← Template de arquivo de migração
│   └── versions/                 ← Migrações geradas
├── Docs/
│   └── database_uml.md           ← ERD (Mermaid)
├── Requisitos/                   ← Histórias de usuário e especificação
└── app/
    ├── main.py                   ← Entry point: app FastAPI + seed inicial
    ├── core/
    │   ├── config.py             ← Settings via pydantic-settings
    │   ├── database.py           ← Engine async + factory de sessão
    │   ├── security.py           ← JWT, bcrypt
    │   └── dependencies.py       ← FastAPI deps: auth, RBAC, IP extractor
    ├── shared/
    │   ├── base_model.py         ← Mixins: UUID PK, timestamps, audit user
    │   └── pagination.py         ← Resposta paginada genérica
    └── modules/
        ├── auth/                 ← models · schemas · service · router
        ├── contacts/             ← models · schemas · service · router
        ├── accounts/             ← models · schemas · service · router
        ├── opportunities/        ← models · schemas · service · router
        └── audit/                ← models · schemas · service · router
```

---

## Credenciais Padrão

> **Atenção:** Altere todas as credenciais abaixo antes de qualquer deploy.

| Serviço | Usuário / Login | Senha |
|---|---|---|
| API (admin) | `admin@crm.local` | `Admin@1234` |
| pgAdmin | `admin@crm.local` | `admin123` |
| PostgreSQL | `crm_user` | `crm_strong_pass_2024` |
| Mailpit | — | sem autenticação |

O usuário admin da API é criado automaticamente no primeiro startup se não houver nenhum usuário cadastrado no banco.

---

## Roadmap

| Fase | Módulos | Status |
|---|---|---|
| **Fase 1 — MVP** | Autenticação, Contatos, Contas, Oportunidades, Pipeline | ✅ Implementado |
| **Fase 2 — Operacional** | Atividades (ACT-001, ACT-002), Relatórios (REP-001 a REP-003), Administração (ADM-001, ADM-002) | Planejado |
| **Fase 3 — Diferencial** | Marketing/Leads (MKT-001 a MKT-003), Suporte/Casos (CAS-001, CAS-002) | Planejado |
| **Fase 4 — Qualidade** | Performance, disponibilidade, observabilidade (NFR-001, NFR-002) | Contínuo |
