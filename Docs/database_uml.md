# CRM Backend — UML do Banco de Dados

## Diagrama Entidade-Relacionamento (Mermaid ERD)

```mermaid
erDiagram
    USERS {
        uuid id PK
        varchar name
        varchar email UK
        varchar password_hash
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }

    ROLES {
        uuid id PK
        varchar name UK
        varchar description
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }

    USER_ROLES {
        uuid user_id FK
        uuid role_id FK
    }

    PERMISSIONS {
        uuid id PK
        uuid role_id FK
        varchar module
        boolean can_create
        boolean can_read
        boolean can_update
        boolean can_delete
    }

    PASSWORD_RESET_TOKENS {
        uuid id PK
        uuid user_id FK
        varchar token UK
        timestamptz expires_at
        timestamptz used_at
        timestamptz created_at
    }

    CONTACTS {
        uuid id PK
        varchar name
        varchar email
        varchar phone
        varchar cargo
        varchar lead_source
        text[] tags
        text notes
        boolean is_active
        uuid owner_id FK
        uuid created_by FK
        uuid updated_by FK
        timestamptz created_at
        timestamptz updated_at
    }

    ACCOUNTS {
        uuid id PK
        varchar name
        varchar cnpj UK
        varchar segment
        varchar size
        jsonb address
        varchar website
        text notes
        boolean is_active
        uuid parent_id FK
        uuid owner_id FK
        uuid created_by FK
        uuid updated_by FK
        timestamptz created_at
        timestamptz updated_at
    }

    CONTACT_ACCOUNTS {
        uuid contact_id FK
        uuid account_id FK
    }

    PIPELINE_STAGES {
        uuid id PK
        varchar name
        int order
        numeric probability
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }

    OPPORTUNITIES {
        uuid id PK
        varchar title
        uuid contact_id FK
        uuid account_id FK
        numeric value
        date close_date
        numeric probability
        uuid stage_id FK
        varchar source
        varchar status
        text lost_reason
        text notes
        uuid owner_id FK
        timestamptz closed_at
        uuid closed_by
        uuid created_by FK
        uuid updated_by FK
        timestamptz created_at
        timestamptz updated_at
    }

    AUDIT_LOGS {
        uuid id PK
        varchar entity_type
        uuid entity_id
        varchar action
        uuid user_id
        varchar ip_address
        varchar user_agent
        jsonb old_values
        jsonb new_values
        timestamptz created_at
    }

    USERS ||--o{ USER_ROLES : "possui"
    ROLES ||--o{ USER_ROLES : "atribuído a"
    ROLES ||--o{ PERMISSIONS : "define"
    USERS ||--o{ PASSWORD_RESET_TOKENS : "solicita"
    CONTACTS }o--o{ CONTACT_ACCOUNTS : "pertence a"
    ACCOUNTS }o--o{ CONTACT_ACCOUNTS : "possui"
    ACCOUNTS ||--o{ ACCOUNTS : "pai de (hierarquia)"
    USERS ||--o{ CONTACTS : "responsável por (owner)"
    USERS ||--o{ ACCOUNTS : "responsável por (owner)"
    USERS ||--o{ OPPORTUNITIES : "responsável por (owner)"
    CONTACTS ||--o{ OPPORTUNITIES : "vinculada a"
    ACCOUNTS ||--o{ OPPORTUNITIES : "vinculada a"
    PIPELINE_STAGES ||--o{ OPPORTUNITIES : "contém"
```

---

## Descrição das Tabelas

### `users`
Usuários do sistema. Armazena credenciais com hash bcrypt. Relaciona-se com papéis (`roles`) via tabela de junção.

### `roles`
Papéis de acesso (admin, manager, seller, viewer). Cada papel possui um conjunto de permissões por módulo.

### `user_roles`
Tabela de junção N:N entre `users` e `roles`.

### `permissions`
Permissões por módulo associadas a um papel. Módulos: `contacts`, `accounts`, `opportunities`, `pipeline`, `reports`, `admin`, `audit`.

### `password_reset_tokens`
Tokens temporários para recuperação de senha. Expiram após período configurável e são invalidados após uso.

### `contacts`
Pessoas físicas / prospects do CRM. Suporta tags (array), múltiplas contas vinculadas e rastreio de origem do lead.

### `accounts`
Empresas (contas). Suporta hierarquia matriz/filial via auto-referência `parent_id`. CNPJ único. Endereço armazenado como JSONB.

### `contact_accounts`
Tabela de junção N:N entre `contacts` e `accounts`.

### `pipeline_stages`
Estágios do funil de vendas. Ordenados por `order`. Probabilidade padrão por estágio para cálculo de receita prevista.

### `opportunities`
Oportunidades de venda. Vinculada obrigatoriamente a um contato e uma conta. Status: `active`, `won`, `lost`. Motivo de perda obrigatório quando `status = lost`.

### `audit_logs`
Registro imutável de operações críticas. Armazena estado anterior (`old_values`) e novo (`new_values`) como JSONB. Filtrável por entidade, ação, usuário e período.

---

## Módulos e Entidades (por Domínio)

```
┌─────────────────────────────────────────────────────────────────┐
│  DOMÍNIO: auth                                                    │
│  users · roles · user_roles · permissions · password_reset_tokens│
├─────────────────────────────────────────────────────────────────┤
│  DOMÍNIO: contacts                                                │
│  contacts · contact_accounts                                      │
├─────────────────────────────────────────────────────────────────┤
│  DOMÍNIO: accounts                                                │
│  accounts                                                         │
├─────────────────────────────────────────────────────────────────┤
│  DOMÍNIO: opportunities                                           │
│  pipeline_stages · opportunities                                  │
├─────────────────────────────────────────────────────────────────┤
│  DOMÍNIO: audit                                                   │
│  audit_logs                                                       │
└─────────────────────────────────────────────────────────────────┘
```

> Cada domínio corresponde a um módulo na estrutura de código e é candidato
> a se tornar um microserviço independente em fases futuras.
