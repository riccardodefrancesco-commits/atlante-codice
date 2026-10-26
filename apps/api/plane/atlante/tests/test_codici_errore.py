# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A code for every error (docs/proposta-codici-errore.md): the person sees it, the log has it with
page, action and the person's id, never the request's data."""

import logging
import re

import pytest

from plane.atlante.error_codes import ALPHABET, new_code
from plane.atlante.tests.conftest import logged_in
from plane.atlante.views import ClientEndpoint

CODE = re.compile(r"^ATL-[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{4}$")


@pytest.fixture
def error_log(caplog):
    logger = logging.getLogger("plane.exception")
    logger.addHandler(caplog.handler)
    yield caplog
    logger.removeHandler(caplog.handler)


@pytest.mark.unit
def test_codes_are_short_and_easy_to_read():
    codes = {new_code() for _ in range(200)}
    assert all(CODE.match(code) for code in codes)
    assert not set("01OI") & set(ALPHABET)
    assert len(codes) > 190  # practically never the same twice


@pytest.mark.contract
@pytest.mark.django_db
def test_an_unexpected_error_answers_with_its_code_and_logs_it(team, error_log, monkeypatch):
    def broken(self, request, slug):
        raise RuntimeError("guasto inventato")

    monkeypatch.setattr(ClientEndpoint, "get", broken)
    response = logged_in(team.admin).get(f"{team.base}/clients/", {"cerca": "dato-del-cliente-inventato"})

    assert response.status_code == 500
    code = response.data["codice"]
    assert CODE.match(code)
    assert response.data["error"] == f"Qualcosa non ha funzionato. Codice: {code}. Riprova o segnalalo."
    record = next(r for r in error_log.records if getattr(r, "codice", None) == code)
    assert record.path == "/api/atlante/workspaces/spazio-prova/clients/"
    assert record.method == "GET"
    assert record.user_id == str(team.admin.id)
    # The request's values never reach the log.
    assert "dato-del-cliente-inventato" not in error_log.text


@pytest.mark.contract
@pytest.mark.django_db
def test_a_page_that_breaks_in_the_browser_sends_its_code(team, error_log):
    member = logged_in(team.membro)
    response = member.post(
        "/api/atlante/errori/", {"codice": "ATL-7F3K", "pagina": "/spazio-prova/clients/", "tipo": "TypeError"}, format="json"
    )

    assert response.status_code == 204
    record = next(r for r in error_log.records if getattr(r, "codice", None) == "ATL-7F3K")
    assert (record.path, record.method, record.tipo, record.user_id) == (
        "/spazio-prova/clients/", "BROWSER", "TypeError", str(team.membro.id),
    )
    assert member.post("/api/atlante/errori/", {"codice": "rm -rf"}, format="json").status_code == 400
