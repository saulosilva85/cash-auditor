# Arquitetura — Cash Auditor

Sistema de contagem de cédulas em tempo real para um banco estadual com uma
**agência central** e **100+ agências** distribuídas. Cada agência possui de 1 a 2
**máquinas contadoras** conectadas à rede. Quando uma contadora conclui uma
contagem, o resultado é enviado automaticamente ao servidor central e exibido em
tempo real nos **dashboards** dos gerentes.

## Visão geral

```mermaid
flowchart LR
    subgraph AG1["🏦 Agência 0002 (Norte)"]
        C1["🖥️ Contadora 01<br/>+ agente"]
        C2["🖥️ Contadora 02<br/>+ agente"]
    end
    subgraph AG2["🏦 Agência 0003 (Sul)"]
        C3["🖥️ Contadora 01<br/>+ agente"]
    end
    subgraph AGN["🏦 Agência N (100+)"]
        CN["🖥️ Contadoras 1-2<br/>+ agente"]
    end

    subgraph CENTRAL["🏛️ Servidor Central (Agência 0001)"]
        API["FastAPI<br/>REST + WebSocket"]
        DB[("Banco de dados<br/>SQLite / PostgreSQL")]
        WEB["Frontend SPA<br/>(dashboards)"]
        API <--> DB
        API --> WEB
    end

    GER["👔 Gerentes<br/>(navegadores)"]

    C1 -- "POST /api/contagens/ingest<br/>(HTTP, api_key)" --> API
    C2 -- "POST /api/contagens/ingest" --> API
    C3 -- "POST /api/contagens/ingest" --> API
    CN -- "POST /api/contagens/ingest" --> API

    API -- "WebSocket /ws<br/>(broadcast: nova_contagem)" --> GER
    WEB -. "carrega" .-> GER
```

## Fluxo de uma contagem em tempo real

```mermaid
sequenceDiagram
    participant M as Contadora (agente)
    participant A as API FastAPI (central)
    participant DB as Banco de dados
    participant WS as WebSocket Manager
    participant G as Dashboard (gerente)

    G->>A: abre dashboard / conecta WebSocket (/ws)
    A-->>G: conexão estabelecida (tempo real ativo)

    Note over M: operador finaliza a contagem
    M->>A: POST /api/contagens/ingest { api_key, denominações... }
    A->>A: valida api_key da contadora
    A->>DB: grava Contagem + atualiza status da contadora
    A->>WS: broadcast("nova_contagem", contagem)
    WS-->>G: push em tempo real
    A-->>M: 201 Created
    G->>G: atualiza KPIs, gráficos e feed ao vivo
```

## Componentes

| Componente | Responsabilidade | Tecnologia |
|---|---|---|
| **Agente da contadora** | Lê o resultado da máquina e faz POST autenticado para a central | Qualquer linguagem (HTTP). Simulador em Python incluso |
| **API** | REST (cadastros + ingestão) e WebSocket (broadcast) | FastAPI / Uvicorn |
| **Banco de dados** | Persiste agências, contadoras e contagens | SQLite (dev) → PostgreSQL (produção) |
| **WebSocket Manager** | Mantém dashboards conectados e transmite eventos | FastAPI WebSockets |
| **Frontend (dashboards)** | KPIs, gráficos, ranking de agências, feed ao vivo, cadastros | SPA (HTML/CSS/JS + Chart.js) |

## Modelo de dados

```mermaid
erDiagram
    AGENCIA ||--o{ CONTADORA : possui
    CONTADORA ||--o{ CONTAGEM : gera
    AGENCIA ||--o{ CONTAGEM : registra

    AGENCIA {
        int id PK
        string codigo UK
        string nome
        string cidade
        string regiao
        bool central
        bool ativa
    }
    CONTADORA {
        int id PK
        string numero_serie UK
        string api_key
        string status
        int agencia_id FK
    }
    CONTAGEM {
        int id PK
        float valor_total
        int total_cedulas
        int cedulas_rejeitadas
        json denominacoes
        datetime finalizada_em
        int contadora_id FK
        int agencia_id FK
    }
```

## Decisões de projeto

- **Autenticação das contadoras por `api_key`**: cada contadora recebe uma chave
  única no cadastro. O agente envia essa chave no POST; a central identifica a
  contadora e a agência automaticamente — não é preciso configurar IDs no campo.
- **Tempo real via WebSocket**: a ingestão grava no banco e imediatamente faz
  *broadcast* para todos os dashboards conectados, sem polling.
- **Ingestão desacoplada**: o agente da contadora pode ser escrito em qualquer
  linguagem; basta um POST HTTP. Isso facilita a integração com fabricantes
  diferentes de máquinas.
- **Banco plugável**: SQLite para desenvolvimento; em produção basta definir
  `DATABASE_URL` para um PostgreSQL (a central concentra 100+ agências).
- **Escala**: para muitas agências/instâncias, o `ConnectionManager` em memória
  pode ser trocado por um broker (Redis Pub/Sub) sem mudar o frontend.
