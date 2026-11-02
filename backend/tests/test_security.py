import pytest
from fastapi import HTTPException

from app.security import Level, Role, allowed_levels, resolve_role


def test_resolve_role(settings):
    assert resolve_role("key-student", settings) is Role.STUDENT
    assert resolve_role("key-direction", settings) is Role.DIRECTION
    assert resolve_role("key-admin", settings) is Role.ADMIN
    assert resolve_role("mauvaise-cle", settings) is None
    assert resolve_role(None, settings) is None


def test_student_is_limited_to_level1():
    assert allowed_levels(Role.STUDENT) == [Level.LEVEL1]
    with pytest.raises(HTTPException) as exc:
        allowed_levels(Role.STUDENT, [Level.LEVEL2])
    assert exc.value.status_code == 403


def test_direction_can_restrict_scope():
    assert allowed_levels(Role.DIRECTION) == [Level.LEVEL1, Level.LEVEL2]
    assert allowed_levels(Role.DIRECTION, [Level.LEVEL1]) == [Level.LEVEL1]
    assert allowed_levels(Role.DIRECTION, [Level.LEVEL2, Level.LEVEL2]) == [Level.LEVEL2]
