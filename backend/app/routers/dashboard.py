"""Endpoint de resumo consolidado para os dashboards."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
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
def resumo(
    inicio: date | None = Query(default=None, description="Data inicial (AAAA-MM-DD)"),
    fim: date | None = Query(default=None, description="Data final (AAAA-MM-DD)"),
    session: Session = Depends(get_session),
) -> DashboardResumo:
    agora = datetime.now(timezone.utc)

    # Define o período de análise. Sem datas → considera apenas o dia de hoje.
    if inicio or fim:
        d_ini = inicio or fim
        d_fim = fim or inicio
        if d_fim < d_ini:
            d_ini, d_fim = d_fim, d_ini
        periodo_inicio = datetime(
            d_ini.year, d_ini.month, d_ini.day, tzinfo=timezone.utc
        )
        periodo_fim = datetime(
            d_fim.year, d_fim.month, d_fim.day, 23, 59, 59, 999999, tzinfo=timezone.utc
        )
        if d_ini == d_fim:
            periodo_label = d_ini.strftime("%d/%m/%Y")
        else:
            periodo_label = (
                f"{d_ini.strftime('%d/%m/%Y')} – {d_fim.strftime('%d/%m/%Y')}"
            )
    else:
        periodo_inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        periodo_fim = None
        periodo_label = "hoje"

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

    def _no_periodo(c: Contagem) -> bool:
        ts = _finalizada(c)
        if ts < periodo_inicio:
            return False
        if periodo_fim is not None and ts > periodo_fim:
            return False
        return True

    contagens_periodo = [c for c in contagens if _no_periodo(c)]

    valor_total_hoje = sum(c.valor_total for c in contagens_periodo)
    total_cedulas_hoje = sum(c.total_cedulas for c in contagens_periodo)
    rejeitadas_hoje = sum(c.cedulas_rejeitadas for c in contagens_periodo)
    valor_total_geral = sum(c.valor_total for c in contagens)

    # Quebra por denominação (do período).
    por_denom_qtd: dict[str, int] = defaultdict(int)
    for c in contagens_periodo:
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
    for c in contagens_periodo:
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

    # Série temporal: por hora (1-2 dias) ou por dia (períodos maiores).
    buckets: dict[str, float] = {}
    if periodo_fim is None:
        # Padrão: últimas 24h, por hora.
        for h in range(23, -1, -1):
            rotulo = (agora - timedelta(hours=h)).strftime("%H:00")
            buckets[rotulo] = 0.0
        for c in contagens:
            ts = _finalizada(c)
            if (agora - ts) <= timedelta(hours=24):
                rotulo = ts.strftime("%H:00")
                if rotulo in buckets:
                    buckets[rotulo] += c.valor_total
        serie_titulo = "Valor por hora (24h)"
    else:
        dias = (periodo_fim.date() - periodo_inicio.date()).days + 1
        if dias <= 2:
            for h in range(24):
                buckets[f"{h:02d}:00"] = 0.0
            for c in contagens_periodo:
                rotulo = _finalizada(c).strftime("%H:00")
                if rotulo in buckets:
                    buckets[rotulo] += c.valor_total
            serie_titulo = "Valor por hora"
        else:
            d = periodo_inicio.date()
            while d <= periodo_fim.date():
                buckets[d.strftime("%d/%m")] = 0.0
                d += timedelta(days=1)
            for c in contagens_periodo:
                rotulo = _finalizada(c).strftime("%d/%m")
                if rotulo in buckets:
                    buckets[rotulo] += c.valor_total
            serie_titulo = "Valor por dia"
    serie_horaria = [{"hora": k, "valor": v} for k, v in buckets.items()]

    return DashboardResumo(
        total_agencias=len(agencias),
        total_contadoras=len(contadoras),
        contadoras_online=contadoras_online,
        total_contagens_hoje=len(contagens_periodo),
        valor_total_hoje=valor_total_hoje,
        total_cedulas_hoje=total_cedulas_hoje,
        cedulas_rejeitadas_hoje=rejeitadas_hoje,
        valor_total_geral=valor_total_geral,
        por_denominacao=por_denominacao,
        top_agencias=top_agencias[:10],
        serie_horaria=serie_horaria,
        periodo_label=periodo_label,
        serie_titulo=serie_titulo,
    )
