"""Endpoints de cadastro de agências."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from ..database import get_session
from ..models import Agencia, Contadora
from ..schemas import AgenciaCreate, AgenciaRead, AgenciaUpdate

router = APIRouter(prefix="/api/agencias", tags=["agencias"])


def _to_read(session: Session, agencia: Agencia) -> AgenciaRead:
    total = len(
        session.exec(select(Contadora).where(Contadora.agencia_id == agencia.id)).all()
    )
    data = AgenciaRead.model_validate(agencia)
    data.total_contadoras = total
    return data


@router.get("", response_model=list[AgenciaRead])
def listar_agencias(session: Session = Depends(get_session)) -> list[AgenciaRead]:
    agencias = session.exec(select(Agencia).order_by(Agencia.codigo)).all()
    return [_to_read(session, a) for a in agencias]


@router.post("", response_model=AgenciaRead, status_code=201)
def criar_agencia(
    payload: AgenciaCreate, session: Session = Depends(get_session)
) -> AgenciaRead:
    existente = session.exec(
        select(Agencia).where(Agencia.codigo == payload.codigo)
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Já existe uma agência com esse código.")
    agencia = Agencia(**payload.model_dump())
    session.add(agencia)
    session.commit()
    session.refresh(agencia)
    return _to_read(session, agencia)


@router.get("/{agencia_id}", response_model=AgenciaRead)
def obter_agencia(
    agencia_id: int, session: Session = Depends(get_session)
) -> AgenciaRead:
    agencia = session.get(Agencia, agencia_id)
    if not agencia:
        raise HTTPException(status_code=404, detail="Agência não encontrada.")
    return _to_read(session, agencia)


@router.patch("/{agencia_id}", response_model=AgenciaRead)
def atualizar_agencia(
    agencia_id: int,
    payload: AgenciaUpdate,
    session: Session = Depends(get_session),
) -> AgenciaRead:
    agencia = session.get(Agencia, agencia_id)
    if not agencia:
        raise HTTPException(status_code=404, detail="Agência não encontrada.")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(agencia, campo, valor)
    session.add(agencia)
    session.commit()
    session.refresh(agencia)
    return _to_read(session, agencia)


@router.delete("/{agencia_id}", status_code=204, response_class=Response)
def remover_agencia(
    agencia_id: int, session: Session = Depends(get_session)
) -> Response:
    agencia = session.get(Agencia, agencia_id)
    if not agencia:
        raise HTTPException(status_code=404, detail="Agência não encontrada.")
    session.delete(agencia)
    session.commit()
    return Response(status_code=204)
