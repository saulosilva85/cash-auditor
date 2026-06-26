# Cash Auditor

Sistema de **contagem de cédulas em tempo real** para um banco estadual com uma
agência **central** e **100+ agências** distribuídas. Cada agência tem de 1 a 2
**máquinas contadoras** conectadas à rede. Quando uma contadora conclui uma
contagem, o resultado é enviado automaticamente ao servidor central e exibido em
tempo real nos **dashboards** dos gerentes.

## Funcionalidades

- **Dashboard em tempo real**: KPIs (valor contado, cédulas, contagens,
  contadoras online), gráfico de valor por hora, distribuição por denominação,
  ranking de agências e **feed ao vivo** das contagens.
- **Cadastro de agências**: criar, editar, ativar/inativar e remover agências.
- **Cadastro de contadoras**: criar e gerenciar contadoras, cada uma com uma
  **chave de API** própria usada pela máquina para enviar contagens.
- **Ingestão automática**: ao finalizar a contagem, a contadora faz um `POST`
  e o resultado é transmitido na hora para todos os dashboards via **WebSocket**.
- **Simulador**: script que simula contadoras enviando contagens, para demonstrar
  o tempo real.

## Arquitetura

Veja o detalhamento (com diagramas) em [`docs/architecture.md`](docs/architecture.md).

```
Agência (1-2 contadoras)                Servidor Central (Agência 0001)
┌────────────────────┐   POST /ingest   ┌──────────────────────────────────┐
│ Contadora + agente │ ───────────────▶ │  API FastAPI (REST + WebSocket)  │
└────────────────────┘  (HTTP, api_key) │   ├─ cadastros (agências/contad.) │
        ... 100+ agências               │   ├─ ingestão de contagens        │
                                         │   └─ banco de dados               │
                                         │            │ broadcast            │
                                         │            ▼ (WebSocket /ws)       │
                                         │   Dashboards  ───▶ 👔 Gerentes     │
                                         └──────────────────────────────────┘
```

- **Backend**: Python + [FastAPI](https://fastapi.tiangolo.com/) (REST + WebSocket), [SQLModel](https://sqlmodel.tiangolo.com/).
- **Banco**: SQLite no desenvolvimento; PostgreSQL em produção (via `DATABASE_URL`).
- **Frontend**: SPA moderna (HTML/CSS/JS + Chart.js), servida pela própria API.

## Como rodar

Pré-requisito: Python 3.11+.

```bash
# 1. Instalar dependências
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# 2. (Opcional) Popular com dados de exemplo (40 agências + contadoras + contagens)
python -m backend.app.seed

# 3. Subir o servidor (API + dashboard)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 4. Abrir o dashboard
#    http://localhost:8000
#    Documentação da API: http://localhost:8000/docs
```

### Demonstração do tempo real

Com o servidor rodando, em outro terminal:

```bash
source .venv/bin/activate
python simulator/simulator.py --intervalo 3
```

As contagens vão aparecendo no dashboard instantaneamente (feed ao vivo, KPIs e
gráficos se atualizam sozinhos).

## Integração de uma contadora real

Cada contadora cadastrada recebe uma `api_key`. O agente da máquina (em qualquer
linguagem) faz, ao concluir a contagem:

```http
POST /api/contagens/ingest
Content-Type: application/json

{
  "api_key": "ck_xxxxxxxxxxxxxxxx",
  "denominacoes": { "100": 50, "50": 30, "20": 80, "10": 120 },
  "cedulas_rejeitadas": 2,
  "operador": "Maria",
  "lote": "LOTE-2025-0420"
}
```

O servidor calcula `valor_total` e `total_cedulas` automaticamente (se não
enviados), grava no banco e transmite o resultado para os dashboards.

## Executável para Windows Server (`cash_auditor.exe`)

Para instalar no servidor da central **sem precisar de Python**, o projeto gera um
executável único `cash_auditor.exe` (API + dashboard embutidos). Ao iniciar, ele
sobe o servidor e abre o dashboard no navegador (`http://localhost:8000`).

**Onde baixar o `.exe`:** ele é compilado automaticamente pelo GitHub Actions
(runner Windows) a cada push na `main`. Baixe em **Actions → workflow
`build-windows-exe` → run mais recente → artifact `cash_auditor-exe`**. Ao criar
uma tag `vX.Y.Z`, o `.exe` também é anexado à **Release**.

> O workflow está versionado em [`docs/ci/build-windows.yml`](docs/ci/build-windows.yml)
> e precisa ser movido **uma vez** para `.github/workflows/` para ativar (veja
> [`docs/deploy-windows.md`](docs/deploy-windows.md)).

**Instalação no servidor (homologação → produção):**

1. Copie o `cash_auditor.exe` para uma pasta no servidor (ex.: `C:\CashAuditor\`).
2. Dê um duplo-clique (ou rode pelo Prompt). O banco **SQLite** é criado ao lado
   do `.exe` (`cash_auditor.db`) e persiste entre reinícios.
3. Acesse o dashboard em `http://localhost:8000` (ou pelo IP do servidor na rede).

**Variáveis de ambiente úteis** (defina antes de iniciar):

| Variável | Padrão | Descrição |
|---|---|---|
| `CASH_AUDITOR_HOST` | `127.0.0.1` | Use `0.0.0.0` para aceitar acesso de outras máquinas da rede. |
| `CASH_AUDITOR_PORT` | `8000` | Porta do servidor. |
| `CASH_AUDITOR_NO_BROWSER` | — | `1` para não abrir o navegador (útil ao rodar como serviço). |
| `DATABASE_URL` | SQLite ao lado do `.exe` | Em produção, aponte para PostgreSQL. |

O passo a passo completo (rodar como **serviço do Windows**, liberar firewall,
promover de homologação para produção e backup) está em
[`docs/deploy-windows.md`](docs/deploy-windows.md).

**Compilar o `.exe` localmente** (opcional, exige Windows com Python):

```powershell
pip install -r packaging/requirements-build.txt
pyinstaller packaging/cash_auditor.spec --noconfirm
# resultado em dist/cash_auditor.exe
```

## Estrutura do projeto

```
backend/
  app/
    main.py            # app FastAPI: rotas, WebSocket, frontend
    config.py          # configuração (DATABASE_URL etc.)
    database.py        # engine e sessões
    models.py          # tabelas: Agencia, Contadora, Contagem
    schemas.py         # schemas de entrada/saída
    realtime.py        # ConnectionManager (WebSocket broadcast)
    seed.py            # dados de exemplo
    routers/           # agencias, contadoras, contagens, dashboard
  requirements.txt
frontend/
  index.html
  static/css/styles.css
  static/js/app.js
  static/js/chart.umd.min.js
simulator/
  simulator.py         # simula contadoras enviando contagens
packaging/
  launcher.py          # ponto de entrada do executável (sobe uvicorn + abre o navegador)
  cash_auditor.spec    # configuração do PyInstaller (gera cash_auditor.exe)
  requirements-build.txt
docs/
  architecture.md      # diagramas (Mermaid) e decisões de projeto
  deploy-windows.md    # instalação no Windows Server (homologação → produção)
```

## Configuração

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | `sqlite:///backend/cash_auditor.db` | Conexão do banco. Em produção, use PostgreSQL. |
| `CASH_AUDITOR_HOST` | `127.0.0.1` | Host do executável. Use `0.0.0.0` para acesso pela rede. |
| `CASH_AUDITOR_PORT` | `8000` | Porta do executável. |
| `CASH_AUDITOR_NO_BROWSER` | — | `1` para não abrir o navegador ao iniciar o `.exe`. |
