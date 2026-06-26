"""Endpoints de cadastro de contadoras de cédulas."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from ..database import get_session
from ..models import Agencia, Contadora
from ..schemas import ContadoraCreate, ContadoraRead, ContadoraUpdate

router = APIRouter(prefix="/api/contadoras", tags=["contadoras"])


def _to_read(session: Session, contadora: Contadora) -> ContadoraRead:
    data = ContadoraRead.model_validate(contadora)
    agencia = session.get(Agencia, contadora.agencia_id)
    data.agencia_nome = agencia.nome if agencia else None
    return data


@router.get("", response_model=list[ContadoraRead])
def listar_contadoras(
    agencia_id: int | None = None, session: Session = Depends(get_session)
) -> list[ContadoraRead]:
    query = select(Contadora).order_by(Contadora.numero_serie)
    if agencia_id is not None:
        query = query.where(Contadora.agencia_id == agencia_id)
    contadoras = session.exec(query).all()
    return [_to_read(session, c) for c in contadoras]


@router.post("", response_model=ContadoraRead, status_code=201)
def criar_contadora(
    payload: ContadoraCreate, session: Session = Depends(get_session)
) -> ContadoraRead:
    agencia = session.get(Agencia, payload.agencia_id)
    if not agencia:
        raise HTTPException(status_code=400, detail="Agência informada não existe.")
    existente = session.exec(
        select(Contadora).where(Contadora.numero_serie == payload.numero_serie)
    ).first()
    if existente:
        raise HTTPException(
            status_code=409, detail="Já existe uma contadora com esse número de série."
        )
    contadora = Contadora(
        **payload.model_dump(),
        api_key=f"ck_{secrets.token_hex(16)}",
    )
    session.add(contadora)
    session.commit()
    session.refresh(contadora)
    return _to_read(session, contadora)


@router.get("/{contadora_id}", response_model=ContadoraRead)
def obter_contadora(
    contadora_id: int, session: Session = Depends(get_session)
) -> ContadoraRead:
    contadora = session.get(Contadora, contadora_id)
    if not contadora:
        raise HTTPException(status_code=404, detail="Contadora não encontrada.")
    return _to_read(session, contadora)


@router.patch("/{contadora_id}", response_model=ContadoraRead)
def atualizar_contadora(
    contadora_id: int,
    payload: ContadoraUpdate,
    session: Session = Depends(get_session),
) -> ContadoraRead:
    contadora = session.get(Contadora, contadora_id)
    if not contadora:
        raise HTTPException(status_code=404, detail="Contadora não encontrada.")
    dados = payload.model_dump(exclude_unset=True)
    if "agencia_id" in dados and not session.get(Agencia, dados["agencia_id"]):
        raise HTTPException(status_code=400, detail="Agência informada não existe.")
    for campo, valor in dados.items():
        setattr(contadora, campo, valor)
    session.add(contadora)
    session.commit()
    session.refresh(contadora)
    return _to_read(session, contadora)


@router.post("/{contadora_id}/rotacionar-chave", response_model=ContadoraRead)
def rotacionar_chave(
    contadora_id: int, session: Session = Depends(get_session)
) -> ContadoraRead:
    contadora = session.get(Contadora, contadora_id)
    if not contadora:
        raise HTTPException(status_code=404, detail="Contadora não encontrada.")
    contadora.api_key = f"ck_{secrets.token_hex(16)}"
    session.add(contadora)
    session.commit()
    session.refresh(contadora)
    return _to_read(session, contadora)


@router.delete("/{contadora_id}", status_code=204, response_class=Response)
def remover_contadora(
    contadora_id: int, session: Session = Depends(get_session)
) -> Response:
    contadora = session.get(Contadora, contadora_id)
    if not contadora:
        raise HTTPException(status_code=404, detail="Contadora não encontrada.")
    session.delete(contadora)
    session.commit()
    return Response(status_code=204)
