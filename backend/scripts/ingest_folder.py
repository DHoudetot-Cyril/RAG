"""Ingestion en masse d'un dossier de documents via l'API.

Organisation attendue (inspirée du projet de fin d'études) :

    documents/
    ├── niveau1-usagers/      -> level1 (élèves + direction)
    │   ├── reglement-interieur.pdf
    │   └── calendrier.docx
    └── niveau2-direction/    -> level2 (direction uniquement)
        └── budget.xlsx

Usage :
    python scripts/ingest_folder.py ./documents --api http://localhost:8080 --key $ADMIN_API_KEY

Les fichiers déjà ingérés et inchangés sont ignorés automatiquement (empreinte SHA-256).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

SUPPORTED = {".pdf", ".docx", ".pptx", ".txt", ".md"}
FOLDER_LEVELS = {"niveau1": "level1", "level1": "level1", "niveau2": "level2", "level2": "level2"}


def detect_level(path: Path, root: Path) -> str | None:
    for part in path.relative_to(root).parts[:-1]:
        for prefix, level in FOLDER_LEVELS.items():
            if part.lower().startswith(prefix):
                return level
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--api", default=os.getenv("BACKEND_URL", "http://localhost:8080"))
    parser.add_argument("--key", default=os.getenv("ADMIN_API_KEY"), help="clé d'API administrateur")
    args = parser.parse_args()

    if not args.key:
        parser.error("clé administrateur manquante (--key ou variable ADMIN_API_KEY)")
    if not args.folder.is_dir():
        parser.error(f"dossier introuvable : {args.folder}")

    files = sorted(
        p
        for p in args.folder.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED and not p.name.startswith("~$")
    )
    totals = {"ingested": 0, "updated": 0, "unchanged": 0, "skipped": 0, "error": 0}

    with httpx.Client(base_url=args.api, headers={"X-API-Key": args.key}, timeout=600) as client:
        for path in files:
            level = detect_level(path, args.folder)
            if level is None:
                print(f"[ignoré]   {path} (aucun dossier niveau1-*/niveau2-* parent)")
                totals["skipped"] += 1
                continue
            with path.open("rb") as handle:
                response = client.post("/documents", data={"level": level}, files={"file": (path.name, handle)})
            if response.status_code == 201:
                body = response.json()
                totals[body["status"]] += 1
                print(f"[{body['status']:<9}] {path} -> {level} ({body['chunks']} chunks)")
            else:
                totals["error"] += 1
                print(f"[erreur]   {path} : {response.status_code} {response.text}", file=sys.stderr)

    print("\nRésumé : " + ", ".join(f"{k}={v}" for k, v in totals.items()))
    return 1 if totals["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
