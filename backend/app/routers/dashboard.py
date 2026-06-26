"""Endpoint de resumo consolidado para os dashboards."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import Agencia, Contadora, Contagem
from ..routers.contagens import VALOR_DENOMINACAO
from ..schemas import (
    AgenciaResumo,
    DashboardResumo,
    ResumoDenominacao,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Contadora é considerada online se teve atividade nos últimos N minutos.
JANELA_ONLINE = timedelta(minutes=10)


@router.get("/resumo", response_model=DashboardResumo)
def resumo(session: Session = Depends(get_session)) -> DashboardResumo:
    agora = datetime.now(timezone.utc)
    inicio_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)

    agencias = session.exec(select(Agencia)).all()
    contadoras = session.exec(select(Contadora)).all()
    contagens = session.exec(select(Contagem)).all()

    def _online(c: Contadora) -> bool:
        if not c.ultima_atividade:
            return False
        ts = c.ultima_atividade
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (agora - ts) <= JANELA_ONLINE

    contadoras_online = sum(1 for c in contadoras if _online(c))

    def _finalizada(c: Contagem) -> datetime:
        ts = c.finalizada_em
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts

    contagens_hoje = [c for c in contagens if _finalizada(c) >= inicio_dia]

    valor_total_hoje = sum(c.valor_total for c in contagens_hoje)
    total_cedulas_hoje = sum(c.total_cedulas for c in contagens_hoje)
    rejeitadas_hoje = sum(c.cedulas_rejeitadas for c in contagens_hoje)
    valor_total_geral = sum(c.valor_total for c in contagens)

    # Quebra por denominação (do dia).
    por_denom_qtd: dict[str, int] = defaultdict(int)
    for c in contagens_hoje:
        for k, v in (c.denominacoes or {}).items():
            por_denom_qtd[k] += int(v)
    por_denominacao = [
        ResumoDenominacao(
            denominacao=k,
            quantidade=por_denom_qtd[k],
            valor=por_denom_qtd[k] * VALOR_DENOMINACAO.get(k, 0),
        )
        for k in sorted(por_denom_qtd, key=lambda x: int(x))
    ]

    # Ranking de agências (do dia).
    contadoras_por_agencia: dict[int, list[Contadora]] = defaultdict(list)
    for c in contadoras:
        contadoras_por_agencia[c.agencia_id].append(c)

    resumo_por_agencia: dict[int, dict] = {}
    for c in contagens_hoje:
        r = resumo_por_agencia.setdefault(
            c.agencia_id, {"valor": 0.0, "cedulas": 0, "contagens": 0}
        )
        r["valor"] += c.valor_total
        r["cedulas"] += c.total_cedulas
        r["contagens"] += 1

    agencias_por_id = {a.id: a for a in agencias}
    top_agencias: list[AgenciaResumo] = []
    for ag_id, r in resumo_por_agencia.items():
        ag = agencias_por_id.get(ag_id)
        if not ag:
            continue
        cont_ag = contadoras_por_agencia.get(ag_id, [])
        top_agencias.append(
            AgenciaResumo(
                agencia_id=ag_id,
                codigo=ag.codigo,
                nome=ag.nome,
                cidade=ag.cidade,
                regiao=ag.regiao,
                valor_total=r["valor"],
                total_cedulas=r["cedulas"],
                total_contagens=r["contagens"],
                contadoras_online=sum(1 for c in cont_ag if _online(c)),
                total_contadoras=len(cont_ag),
            )
        )
    top_agencias.sort(key=lambda a: a.valor_total, reverse=True)

    # Série horária (últimas 24h).
    buckets: dict[str, float] = {}
    for h in range(23, -1, -1):
        rotulo = (agora - timedelta(hours=h)).strftime("%H:00")
        buckets[rotulo] = 0.0
    for c in contagens:
        ts = _finalizada(c)
        if (agora - ts) <= timedelta(hours=24):
            rotulo = ts.strftime("%H:00")
            if rotulo in buckets:
                buckets[rotulo] += c.valor_total
    serie_horaria = [{"hora": k, "valor": v} for k, v in buckets.items()]

    return DashboardResumo(
        total_agencias=len(agencias),
        total_contadoras=len(contadoras),
        contadoras_online=contadoras_online,
        total_contagens_hoje=len(contagens_hoje),
        valor_total_hoje=valor_total_hoje,
        total_cedulas_hoje=total_cedulas_hoje,
        cedulas_rejeitadas_hoje=rejeitadas_hoje,
        valor_total_geral=valor_total_geral,
        por_denominacao=por_denominacao,
        top_agencias=top_agencias[:10],
        serie_horaria=serie_horaria,
    )
