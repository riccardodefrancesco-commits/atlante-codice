# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Atlante public API (personal API key in the X-Api-Key header), under /api/v1/atlante/.

For n8n and the Claude port. Same rules as the interface: no delete, only archive.
"""

from django.urls import path

from plane.atlante.phase_views import (
    PublicHomeTasksEndpoint,
    PublicProjectRolesEndpoint,
    PublicProjectTemplateEndpoint,
    PublicTaskApprovalEndpoint,
    PublicTaskChoicesEndpoint,
)
from plane.atlante.views import (
    PublicClientArchiveEndpoint,
    PublicClientDetailEndpoint,
    PublicClientEndpoint,
    PublicClientIssuesEndpoint,
    PublicClientRestoreEndpoint,
    PublicProjectClientEndpoint,
)

urlpatterns = [
    path("workspaces/<str:slug>/da-assegnare/", PublicHomeTasksEndpoint.as_view(), name="atlante-public-home-tasks"),
    path("workspaces/<str:slug>/clients/", PublicClientEndpoint.as_view(), name="atlante-public-clients"),
    path("workspaces/<str:slug>/clients/<uuid:pk>/", PublicClientDetailEndpoint.as_view(), name="atlante-public-client"),
    path(
        "workspaces/<str:slug>/clients/<uuid:pk>/archive/",
        PublicClientArchiveEndpoint.as_view(),
        name="atlante-public-client-archive",
    ),
    path(
        "workspaces/<str:slug>/clients/<uuid:pk>/restore/",
        PublicClientRestoreEndpoint.as_view(),
        name="atlante-public-client-restore",
    ),
    path(
        "workspaces/<str:slug>/clients/<uuid:pk>/issues/",
        PublicClientIssuesEndpoint.as_view(),
        name="atlante-public-client-issues",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/client/",
        PublicProjectClientEndpoint.as_view(),
        name="atlante-public-project-client",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/modello/",
        PublicProjectTemplateEndpoint.as_view(),
        name="atlante-public-project-template",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/ruoli/",
        PublicProjectRolesEndpoint.as_view(),
        name="atlante-public-project-roles",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/scelte/",
        PublicTaskChoicesEndpoint.as_view(),
        name="atlante-public-task-choices",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/approvazione/",
        PublicTaskApprovalEndpoint.as_view(),
        name="atlante-public-task-approval",
    ),
]
