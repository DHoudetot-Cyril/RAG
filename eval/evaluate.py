"""Évaluation de la qualité de recherche et de l'isolation des niveaux d'accès.

Pour chaque question du jeu de test, on vérifie :
- **Hit@k**         : le document attendu figure-t-il parmi les k premières sources ?
- **MRR**           : rang moyen inverse du document attendu (1 = toujours premier).
- **Isolation**     : aucun document interdit n'apparaît (ex. un document de direction pour un élève).
- **Latence**       : temps de réponse moyen de la recherche.

Usage (API lancée, documents d'exemple ingérés) :
    python eval/evaluate.py --questions eval/questions.json \
        --student-key $STUDENT_API_KEY --direction-key $DIRECTION_API_KEY
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--questions", type=Path, default=Path(__file__).with_name("questions.json"))
    parser.add_argument("--api", default=os.getenv("BACKEND_URL", "http://localhost:8080"))
    parser.add_argument("--student-key", default=os.getenv("STUDENT_API_KEY"))
    parser.add_argument("--direction-key", default=os.getenv("DIRECTION_API_KEY"))
    args = parser.parse_args()

    keys = {"student": args.student_key, "direction": args.direction_key}
    cases = json.loads(args.questions.read_text(encoding="utf-8"))
    ranks: list[int | None] = []
    latencies: list[float] = []
    leaks = 0

    with httpx.Client(base_url=args.api, timeout=60) as client:
        for case in cases:
            key = keys[case["role"]]
            if not key:
                parser.error(f"clé manquante pour le rôle {case['role']}")
            started = time.perf_counter()
            response = client.post("/search", headers={"X-API-Key": key}, json={"question": case["question"]})
            latencies.append((time.perf_counter() - started) * 1000)
            response.raise_for_status()
            documents = [s["document"] for s in response.json()]

            expected = case.get("expected")
            rank = documents.index(expected) + 1 if expected in documents else None
            if expected:
                ranks.append(rank)
            leaked = sorted(set(documents) & set(case.get("forbidden", [])))
            leaks += bool(leaked)

            status = "✅" if (rank or not expected) and not leaked else "❌"
            detail = f"rang {rank}" if expected else "aucun document attendu"
            if leaked:
                detail += f" | FUITE : {', '.join(leaked)}"
            print(f"{status} [{case['role']:<9}] {case['question']} → {detail}")

    found = [r for r in ranks if r]
    print("\n--- Résultats ---")
    print(f"Hit@k      : {len(found)}/{len(ranks)} ({100 * len(found) / max(len(ranks), 1):.0f} %)")
    print(f"Hit@1      : {sum(r == 1 for r in found)}/{len(ranks)}")
    print(f"MRR        : {sum(1 / r for r in found) / max(len(ranks), 1):.3f}")
    print(f"Isolation  : {'OK' if leaks == 0 else f'{leaks} fuite(s) !'}")
    print(f"Latence    : {statistics.mean(latencies):.0f} ms en moyenne (max {max(latencies):.0f} ms)")
    return 0 if leaks == 0 and len(found) == len(ranks) else 1


if __name__ == "__main__":
    sys.exit(main())
