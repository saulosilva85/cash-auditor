"""Ponto de entrada do executável cash_auditor.exe.

Sobe a API + dashboard (uvicorn) e abre o navegador no endereço local.
Tudo embutido em um único arquivo, sem necessidade de instalar Python no servidor.
"""
from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path

# Garante que o pacote "backend" seja importável quando rodando do código-fonte.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn  # noqa: E402

from backend.app.main import app  # noqa: E402


def main() -> None:
    host = os.getenv("CASH_AUDITOR_HOST", "127.0.0.1")
    port = int(os.getenv("CASH_AUDITOR_PORT", "8000"))
    url = f"http://{host if host != '0.0.0.0' else 'localhost'}:{port}"

    # Abre o dashboard no navegador padrão pouco depois do servidor iniciar.
    if os.getenv("CASH_AUDITOR_NO_BROWSER", "").lower() not in {"1", "true", "sim"}:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    print(f"Cash Auditor iniciado em {url}  (Ctrl+C para encerrar)")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
