"""Contrôle d'accès : chaque rôle possède une clé d'API et un périmètre de niveaux documentaires.

- student   : niveau 1 uniquement (documents publics)
- direction : niveaux 1 et 2
- admin     : niveaux 1 et 2 + ingestion et suppression de documents
"""

import secrets
from enum import StrEnum

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from .config import Settings


class Level(StrEnum):
    LEVEL1 = "level1"
    LEVEL2 = "level2"


class Role(StrEnum):
    STUDENT = "student"
    DIRECTION = "direction"
    ADMIN = "admin"


ROLE_LEVELS: dict[Role, tuple[Level, ...]] = {
    Role.STUDENT: (Level.LEVEL1,),
    Role.DIRECTION: (Level.LEVEL1, Level.LEVEL2),
    Role.ADMIN: (Level.LEVEL1, Level.LEVEL2),
}

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def resolve_role(api_key: str | None, settings: Settings) -> Role | None:
    """Retourne le rôle associé à la clé, en comparaison à temps constant."""
    if not api_key:
        return None
    candidates = {
        Role.ADMIN: settings.admin_api_key,
        Role.DIRECTION: settings.direction_api_key,
        Role.STUDENT: settings.student_api_key,
    }
    for role, expected in candidates.items():
        if expected and secrets.compare_digest(api_key.encode(), expected.encode()):
            return role
    return None


def get_current_role(request: Request, api_key: str | None = Security(api_key_header)) -> Role:
    role = resolve_role(api_key, request.app.state.settings)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé d'API absente ou invalide (en-tête X-API-Key).",
        )
    return role


def require_admin(role: Role = Depends(get_current_role)) -> Role:
    if role is not Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs.")
    return role


def allowed_levels(role: Role, requested: list[Level] | None = None) -> list[Level]:
    """Intersection entre les niveaux demandés et ceux autorisés pour le rôle.

    Lève une 403 si l'utilisateur demande explicitement un niveau interdit.
    """
    permitted = ROLE_LEVELS[role]
    if not requested:
        return list(permitted)
    forbidden = [lvl for lvl in requested if lvl not in permitted]
    if forbidden:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Accès refusé au(x) niveau(x) : {', '.join(lvl.value for lvl in forbidden)}.",
        )
    return list(dict.fromkeys(requested))
