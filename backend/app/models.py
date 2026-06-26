"""Modelos de banco de dados (tabelas) do Cash Auditor."""
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StatusContadora(str, Enum):
    online = "online"
    offline = "offline"
    contando = "contando"
    manutencao = "manutencao"


class Agencia(SQLModel, table=True):
    """Agência bancária (a central é uma agência marcada como `central`)."""

    __tablename__ = "agencias"

    id: int | None = Field(default=None, primary_key=True)
    codigo: str = Field(index=True, unique=True, description="Código da agência, ex.: 0001")
    nome: str
    cidade: str
    regiao: str = Field(default="", description="Região/macrorregião do estado")
    endereco: str = Field(default="")
    gerente: str = Field(default="")
    central: bool = Field(default=False)
    ativa: bool = Field(default=True)
    criada_em: datetime = Field(default_factory=utcnow)

    contadoras: list["Contadora"] = Relationship(
        back_populates="agencia",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Contadora(SQLModel, table=True):
    """Máquina contadora de cédulas instalada em uma agência."""

    __tablename__ = "contadoras"

    id: int | None = Field(default=None, primary_key=True)
    numero_serie: str = Field(index=True, unique=True)
    modelo: str = Field(default="")
    fabricante: str = Field(default="")
    ip: str = Field(default="")
    api_key: str = Field(index=True, description="Chave usada pelo agente para enviar contagens")
    status: StatusContadora = Field(default=StatusContadora.offline)
    ativa: bool = Field(default=True)
    ultima_atividade: datetime | None = Field(default=None)
    criada_em: datetime = Field(default_factory=utcnow)

    agencia_id: int = Field(foreign_key="agencias.id", index=True)
    agencia: Agencia | None = Relationship(back_populates="contadoras")

    contagens: list["Contagem"] = Relationship(
        back_populates="contadora",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Contagem(SQLModel, table=True):
    """Resultado de uma contagem concluída por uma contadora."""

    __tablename__ = "contagens"

    id: int | None = Field(default=None, primary_key=True)
    contadora_id: int = Field(foreign_key="contadoras.id", index=True)
    agencia_id: int = Field(foreign_key="agencias.id", index=True)

    moeda: str = Field(default="BRL")
    valor_total: float = Field(default=0.0)
    total_cedulas: int = Field(default=0)
    cedulas_rejeitadas: int = Field(default=0, description="Cédulas suspeitas/rejeitadas")
    # Quantidade de cédulas por denominação, ex.: {"100": 50, "50": 30}
    denominacoes: dict[str, int] = Field(default_factory=dict, sa_column=Column(JSON))
    operador: str = Field(default="")
    lote: str = Field(default="", description="Identificador do lote/malote")

    iniciada_em: datetime | None = Field(default=None)
    finalizada_em: datetime = Field(default_factory=utcnow)
    criada_em: datetime = Field(default_factory=utcnow)

    contadora: Contadora | None = Relationship(back_populates="contagens")
