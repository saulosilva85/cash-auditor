"""Configuração da engine e sessões do banco de dados."""
from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    """Cria as tabelas (importa os modelos antes para registrá-los)."""
    from . import models  # noqa: F401  (registra os modelos no metadata)

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency do FastAPI que fornece uma sessão de banco."""
    with Session(engine) as session:
        yield session
