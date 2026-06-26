"""Simulador de contadoras de cédulas.

Busca as contadoras cadastradas (e suas chaves) na API e envia contagens
concluídas em intervalos aleatórios, como se fossem máquinas reais finalizando
a contagem em campo. Útil para demonstrar o dashboard em tempo real.

Uso:
    python simulator/simulator.py --url http://localhost:8000 --intervalo 4
"""
from __future__ import annotations

import argparse
import random
import time
from datetime import datetime, timezone

import httpx

DENOMINACOES = ["2", "5", "10", "20", "50", "100", "200"]
OPERADORES = ["Ana", "Bruno", "Carla", "Daniel", "Eduarda", "Felipe", "Gabriela"]


def gerar_contagem() -> dict:
    denoms = {}
    for d in DENOMINACOES:
        if random.random() < 0.75:
            denoms[d] = random.randint(10, 500)
    return {
        "denominacoes": denoms,
        "cedulas_rejeitadas": random.randint(0, 6),
        "operador": random.choice(OPERADORES),
        "lote": f"LOTE-{random.randint(1000, 9999)}",
        "iniciada_em": datetime.now(timezone.utc).isoformat(),
        "finalizada_em": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador de contadoras de cédulas")
    parser.add_argument("--url", default="http://localhost:8000", help="URL base da API")
    parser.add_argument("--intervalo", type=float, default=4.0, help="Segundos entre envios")
    parser.add_argument("--total", type=int, default=0, help="Qtd de envios (0 = infinito)")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.url, timeout=10.0)

    resp = client.get("/api/contadoras")
    resp.raise_for_status()
    contadoras = [c for c in resp.json() if c.get("ativa", True)]
    if not contadoras:
        print("Nenhuma contadora ativa encontrada. Rode o seed primeiro.")
        return
    print(f"{len(contadoras)} contadoras encontradas. Enviando contagens... (Ctrl+C para parar)")

    enviados = 0
    try:
        while True:
            contadora = random.choice(contadoras)
            payload = {"api_key": contadora["api_key"], **gerar_contagem()}
            try:
                r = client.post("/api/contagens/ingest", json=payload)
                r.raise_for_status()
                data = r.json()
                print(
                    f"✓ {data['agencia_codigo']} · {data['contadora_serie']} → "
                    f"R$ {data['valor_total']:,.0f} ({data['total_cedulas']} cédulas)"
                )
            except httpx.HTTPError as exc:
                print(f"✗ Falha ao enviar: {exc}")

            enviados += 1
            if args.total and enviados >= args.total:
                break
            time.sleep(max(0.2, args.intervalo * random.uniform(0.4, 1.6)))
    except KeyboardInterrupt:
        print("\nSimulador encerrado.")


if __name__ == "__main__":
    main()
