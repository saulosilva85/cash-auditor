"""Configurações da aplicação Cash Auditor."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Quando empacotado com PyInstaller (cash_auditor.exe), o app roda "congelado":
# - os recursos (frontend) são extraídos para sys._MEIPASS;
# - o banco SQLite deve ficar ao lado do .exe, para persistir entre execuções.
FROZEN = getattr(sys, "frozen", False)

if FROZEN:
    # Recursos empacotados (frontend) — diretório temporário de extração.
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    # Dados persistentes (banco) — pasta do próprio executável.
    DATA_DIR = Path(sys.executable).resolve().parent
    FRONTEND_DIR = RESOURCE_DIR / "frontend"
    DEFAULT_DB_PATH = DATA_DIR / "cash_auditor.db"
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    RESOURCE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "backend"
    FRONTEND_DIR = BASE_DIR / "frontend"
    DEFAULT_DB_PATH = DATA_DIR / "cash_auditor.db"

# Banco de dados. Em produção, defina DATABASE_URL para um PostgreSQL, ex.:
#   postgresql+psycopg://usuario:senha@host:5432/cash_auditor
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DEFAULT_DB_PATH}",
)

# Título exibido na documentação automática.
APP_TITLE = "Cash Auditor"
APP_VERSION = "1.0.0"
