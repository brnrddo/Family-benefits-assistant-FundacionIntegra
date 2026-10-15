"""Aislamiento del entorno de tests: la suite no depende de ``E3_MOCK`` del shell."""
from __future__ import annotations

import os

from app.api.deps import mock_habilitado


def test_e3_mock_parte_del_default():
    """Cada test parte del default ``E3_MOCK=1`` aunque el shell exporte ``E3_MOCK=0``."""
    assert "E3_MOCK" not in os.environ
    assert mock_habilitado() is True
