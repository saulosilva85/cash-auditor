"""Popula o banco com dados de exemplo (agências, contadoras e contagens).

Uso:
    python -m backend.app.seed
"""
from __future__ import annotations

import random
import secrets
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from .database import engine, init_db
from .models import Agencia, Contadora, Contagem, StatusContadora
from .routers.contagens import VALOR_DENOMINACAO

REGIOES = ["Capital", "Norte", "Sul", "Leste", "Oeste", "Vale", "Litoral", "Serra"]
CIDADES = [
    "Capital", "Santa Rita", "Bela Vista", "Porto Novo", "Vila Real", "São Pedro",
    "Monte Alto", "Rio Claro", "Campo Verde", "Lagoa Seca", "Boa Esperança", "Ouro Preto",
]
FABRICANTES = ["Cash Tech", "MoneyCount", "BankSys", "ContaSegura"]
MODELOS = ["CT-2000", "MC-Pro X", "BS-500", "CS-Vault 9"]
OPERADORES = ["Ana", "Bruno", "Carla", "Daniel", "Eduarda", "Felipe", "Gabriela"]


def _contagem_aleatoria() -> dict[str, int]:
    denoms = {}
    for d in ["2", "5", "10", "20", "50", "100", "200"]:
        if random.random() < 0.8:
            denoms[d] = random.randint(20, 600)
    return denoms


def seed(num_agencias: int = 40) -> None:
    init_db()
    with Session(engine) as session:
        if session.exec(select(Agencia)).first():
            print("Banco já possui dados. Pulando seed.")
            return

        agora = datetime.now(timezone.utc)

        # Agência central.
        central = Agencia(
            codigo="0001",
            nome="Agência Central",
            cidade="Capital",
            regiao="Capital",
            endereco="Av. Principal, 1000 - Centro",
            gerente="Direção Geral",
            central=True,
        )
        session.add(central)

        agencias = [central]
        for i in range(2, num_agencias + 1):
            agencias.append(
                Agencia(
                    codigo=f"{i:04d}",
                    nome=f"Agência {CIDADES[i % len(CIDADES)]} {i:04d}",
                    cidade=CIDADES[i % len(CIDADES)],
                    regiao=REGIOES[i % len(REGIOES)],
                    endereco=f"Rua {i}, {random.randint(10, 999)}",
                    gerente=random.choice(OPERADORES),
                )
            )
        for a in agencias:
            session.add(a)
        session.commit()
        for a in agencias:
            session.refresh(a)

        # Contadoras (1 ou 2 por agência).
        contadoras: list[Contadora] = []
        for a in agencias:
            for n in range(random.randint(1, 2)):
                c = Contadora(
                    numero_serie=f"{a.codigo}-{n + 1:02d}",
                    modelo=random.choice(MODELOS),
                    fabricante=random.choice(FABRICANTES),
                    ip=f"10.{a.id}.0.{n + 10}",
                    api_key=f"ck_{secrets.token_hex(16)}",
                    status=random.choice(
                        [StatusContadora.online, StatusContadora.offline]
                    ),
                    ultima_atividade=agora - timedelta(minutes=random.randint(0, 120)),
                    agencia_id=a.id,
                )
                contadoras.append(c)
                session.add(c)
        session.commit()
        for c in contadoras:
            session.refresh(c)

        # Contagens das últimas 24h.
        total = 0
        for c in contadoras:
            for _ in range(random.randint(2, 8)):
                denoms = _contagem_aleatoria()
                valor = float(
                    sum(VALOR_DENOMINACAO.get(k, 0) * v for k, v in denoms.items())
                )
                cedulas = sum(denoms.values())
                quando = agora - timedelta(
                    hours=random.randint(0, 23), minutes=random.randint(0, 59)
                )
                session.add(
                    Contagem(
                        contadora_id=c.id,
                        agencia_id=c.agencia_id,
                        valor_total=valor,
                        total_cedulas=cedulas,
                        cedulas_rejeitadas=random.randint(0, 8),
                        denominacoes=denoms,
                        operador=random.choice(OPERADORES),
                        lote=f"LOTE-{random.randint(1000, 9999)}",
                        finalizada_em=quando,
                    )
                )
                total += 1
        session.commit()
        print(
            f"Seed concluído: {len(agencias)} agências, "
            f"{len(contadoras)} contadoras, {total} contagens."
        )


if __name__ == "__main__":
    seed()
