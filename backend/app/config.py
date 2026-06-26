"""Configurações da aplicação Cash Auditor."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Banco de dados. Em produção, defina DATABASE_URL para um PostgreSQL, ex.:
#   postgresql+psycopg://usuario:senha@host:5432/cash_auditor
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'backend' / 'cash_auditor.db'}",
)

# Diretório do frontend estático servido pela API.
FRONTEND_DIR = BASE_DIR / "frontend"

# Título exibido na documentação automática.
APP_TITLE = "Cash Auditor"
APP_VERSION = "1.0.0"
