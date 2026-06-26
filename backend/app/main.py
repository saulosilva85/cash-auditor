"""Aplicação principal do Cash Auditor (API + WebSocket + frontend)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import APP_TITLE, APP_VERSION, FRONTEND_DIR
from .database import init_db
from .realtime import manager
from .routers import agencias, contadoras, contagens, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agencias.router)
app.include_router(contadoras.router)
app.include_router(contagens.router)
app.include_router(dashboard.router)


@app.get("/api/health", tags=["infra"])
def health() -> dict:
    return {"status": "ok", "dashboards_conectados": manager.total}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Canal em tempo real: empurra novas contagens para os dashboards."""
    await manager.connect(websocket)
    try:
        while True:
            # Mantém a conexão viva; o cliente pode enviar pings.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)


# Frontend estático (servido na raiz). Mantido por último para não capturar /api.
if FRONTEND_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR / "static")),
        name="static",
    )

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(str(FRONTEND_DIR / "index.html"))
