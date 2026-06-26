"""Schemas Pydantic para entrada/saída da API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .models import StatusContadora


# ---------------------------------------------------------------- Agência
class AgenciaCreate(BaseModel):
    codigo: str
    nome: str
    cidade: str
    regiao: str = ""
    endereco: str = ""
    gerente: str = ""
    central: bool = False
    ativa: bool = True


class AgenciaUpdate(BaseModel):
    nome: str | None = None
    cidade: str | None = None
    regiao: str | None = None
    endereco: str | None = None
    gerente: str | None = None
    central: bool | None = None
    ativa: bool | None = None


class AgenciaRead(BaseModel):
    id: int
    codigo: str
    nome: str
    cidade: str
    regiao: str
    endereco: str
    gerente: str
    central: bool
    ativa: bool
    criada_em: datetime
    total_contadoras: int = 0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------- Contadora
class ContadoraCreate(BaseModel):
    numero_serie: str
    agencia_id: int
    modelo: str = ""
    fabricante: str = ""
    ip: str = ""
    ativa: bool = True


class ContadoraUpdate(BaseModel):
    modelo: str | None = None
    fabricante: str | None = None
    ip: str | None = None
    agencia_id: int | None = None
    status: StatusContadora | None = None
    ativa: bool | None = None


class ContadoraRead(BaseModel):
    id: int
    numero_serie: str
    modelo: str
    fabricante: str
    ip: str
    api_key: str
    status: StatusContadora
    ativa: bool
    ultima_atividade: datetime | None
    criada_em: datetime
    agencia_id: int
    agencia_nome: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------- Contagem
class ContagemIngest(BaseModel):
    """Payload enviado pelo agente da contadora ao concluir a contagem."""

    api_key: str = Field(description="Chave da contadora")
    moeda: str = "BRL"
    valor_total: float | None = None
    total_cedulas: int | None = None
    cedulas_rejeitadas: int = 0
    denominacoes: dict[str, int] = Field(default_factory=dict)
    operador: str = ""
    lote: str = ""
    iniciada_em: datetime | None = None
    finalizada_em: datetime | None = None


class ContagemRead(BaseModel):
    id: int
    contadora_id: int
    agencia_id: int
    moeda: str
    valor_total: float
    total_cedulas: int
    cedulas_rejeitadas: int
    denominacoes: dict[str, int]
    operador: str
    lote: str
    iniciada_em: datetime | None
    finalizada_em: datetime
    criada_em: datetime
    contadora_serie: str | None = None
    agencia_nome: str | None = None
    agencia_codigo: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------- Dashboard
class ResumoDenominacao(BaseModel):
    denominacao: str
    quantidade: int
    valor: float


class AgenciaResumo(BaseModel):
    agencia_id: int
    codigo: str
    nome: str
    cidade: str
    regiao: str
    valor_total: float
    total_cedulas: int
    total_contagens: int
    contadoras_online: int
    total_contadoras: int


class DashboardResumo(BaseModel):
    total_agencias: int
    total_contadoras: int
    contadoras_online: int
    total_contagens_hoje: int
    valor_total_hoje: float
    total_cedulas_hoje: int
    cedulas_rejeitadas_hoje: int
    valor_total_geral: float
    por_denominacao: list[ResumoDenominacao]
    top_agencias: list[AgenciaResumo]
    serie_horaria: list[dict]
    periodo_label: str = "hoje"
    serie_titulo: str = "Valor por hora (24h)"
