# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Every Atlante endpoint, without login or key, answers "not authorized" (docs/regole/sicurezza.md,
level 1 point 2). The list comes from our url files: a new endpoint is checked without writing
anything here."""

import re
import uuid

import pytest
from rest_framework.test import APIClient

from plane.atlante import api_urls, override_urls, urls

MOUNTS = [("/api/atlante/", urls), ("/api/v1/atlante/", api_urls), ("/api/", override_urls)]
METHODS = ("get", "post", "put", "patch", "delete")


def concrete(route):
    """workspaces/<str:slug>/clients/<uuid:pk>/ with invented values."""
    route = re.sub(r"<str:slug>", "spazio-prova", route)
    return re.sub(r"<uuid:\w+>", lambda _: str(uuid.uuid4()), route)


ENDPOINTS = [prefix + concrete(str(pattern.pattern)) for prefix, module in MOUNTS for pattern in module.urlpatterns]


@pytest.mark.contract
@pytest.mark.django_db
@pytest.mark.parametrize("url", ENDPOINTS)
def test_no_endpoint_answers_without_login(url, team):
    nobody = APIClient()
    for method in METHODS:
        status = getattr(nobody, method)(url).status_code
        # 405 means the method does not exist there: no data either way.
        assert status in (401, 403, 405), f"{method.upper()} {url} risponde {status} senza accesso"


def test_the_list_is_not_empty():
    assert len(ENDPOINTS) >= 10
