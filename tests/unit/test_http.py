"""Polite client basics."""

from __future__ import annotations

from exodus.common.http import PoliteClient


def test_user_agent_includes_contact(monkeypatch: object) -> None:
    monkeypatch.setenv("EXODUS_CONTACT_EMAIL", "tester@example.com")
    c = PoliteClient()
    assert "tester@example.com" in c.user_agent
    c.close()
