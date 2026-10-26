# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Plane addresses that Atlante answers itself, with a class that extends Plane's.

Registered before Plane's "api/" (plane/urls.py), so these win; everything else stays Plane's.
Only one for now: the workspace's "all work items", which here can also have groups
(see plane/atlante/workspace_issues.py).
"""

from django.urls import path

from plane.atlante.workspace_issues import AtlanteWorkspaceIssuesViewSet

urlpatterns = [
    path(
        "workspaces/<str:slug>/issues/",
        AtlanteWorkspaceIssuesViewSet.as_view({"get": "list"}),
        name="atlante-global-view-issues",
    ),
]
