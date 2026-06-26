"""Ingestão e consulta de contagens (núcleo do tempo real)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import Agencia, Contadora, Contagem, StatusContadora, utcnow
from ..realtime import manager
from ..schemas import ContagemIngest, ContagemRead

router = APIRouter(prefix="/api/contagens", tags=["contagens"])

# Valor de cada denominação do Real (R$).
VALOR_DENOMINACAO = {
    "2": 2, "5": 5, "10": 10, "20": 20, "50": 50, "100": 100, "200": 200,
}


def _enriquecer(session: Session, contagem: Contagem) -> ContagemRead:
    data = ContagemRead.model_validate(contagem)
    contadora = session.get(Contadora, contagem.contadora_id)
    agencia = session.get(Agencia, contagem.agencia_id)
    data.contadora_serie = contadora.numero_serie if contadora else None
    data.agencia_nome = agencia.nome if agencia else None
    data.agencia_codigo = agencia.codigo if agencia else None
    return data


@router.post("/ingest", response_model=ContagemRead, status_code=201)
async def ingerir_contagem(
    payload: ContagemIngest, session: Session = Depends(get_session)
) -> ContagemRead:
    """Recebe o resultado de uma contagem concluída e o transmite em tempo real.

    Chamado pelo agente da contadora ao finalizar a contagem.
    """
    contadora = session.exec(
        select(Contadora).where(Contadora.api_key == payload.api_key)
    ).first()
    if not contadora:
        raise HTTPException(status_code=401, detail="Chave de contadora inválida.")

    denominacoes = {k: int(v) for k, v in payload.denominacoes.items() if v}

    total_cedulas = payload.total_cedulas
    if total_cedulas is None:
        total_cedulas = sum(denominacoes.values())

    valor_total = payload.valor_total
    if valor_total is None:
        valor_total = float(
            sum(VALOR_DENOMINACAO.get(k, 0) * v for k, v in denominacoes.items())
        )

    contagem = Contagem(
        contadora_id=contadora.id,
        agencia_id=contadora.agencia_id,
        moeda=payload.moeda,
        valor_total=valor_total,
        total_cedulas=total_cedulas,
        cedulas_rejeitadas=payload.cedulas_rejeitadas,
        denominacoes=denominacoes,
        operador=payload.operador,
        lote=payload.lote,
        iniciada_em=payload.iniciada_em,
        finalizada_em=payload.finalizada_em or utcnow(),
    )
    session.add(contagem)

    contadora.status = StatusContadora.online
    contadora.ultima_atividade = utcnow()
    session.add(contadora)

    session.commit()
    session.refresh(contagem)

    resultado = _enriquecer(session, contagem)
    await manager.broadcast("nova_contagem", resultado.model_dump())
    return resultado


@router.get("", response_model=list[ContagemRead])
def listar_contagens(
    agencia_id: int | None = None,
    contadora_id: int | None = None,
    limite: int = Query(default=50, le=500),
    session: Session = Depends(get_session),
) -> list[ContagemRead]:
    query = select(Contagem).order_by(Contagem.finalizada_em.desc()).limit(limite)
    if agencia_id is not None:
        query = query.where(Contagem.agencia_id == agencia_id)
    if contadora_id is not None:
        query = query.where(Contagem.contadora_id == contadora_id)
    contagens = session.exec(query).all()
    return [_enriquecer(session, c) for c in contagens]
