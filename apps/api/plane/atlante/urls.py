# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Atlante endpoints for the interface, under /api/atlante/."""

from django.urls import path

from plane.atlante.phase_views import (
    HomeTasksEndpoint,
    ProjectRolesEndpoint,
    ProjectTemplateEndpoint,
    TaskApprovalEndpoint,
    TaskChoicesEndpoint,
    TemplatesEndpoint,
)
from plane.atlante.views import (
    BrowserErrorEndpoint,
    ClientArchiveEndpoint,
    ClientDetailEndpoint,
    ClientEndpoint,
    ClientIssuesEndpoint,
    ClientProjectsEndpoint,
    ClientRestoreEndpoint,
    IssueClientEndpoint,
    ProjectClientEndpoint,
    ProjectClientMapEndpoint,
    ProjectCodeEndpoint,
)

urlpatterns = [
    path("workspaces/<str:slug>/clients/", ClientEndpoint.as_view(), name="atlante-clients"),
    path("workspaces/<str:slug>/clients/<uuid:pk>/", ClientDetailEndpoint.as_view(), name="atlante-client"),
    path(
        "workspaces/<str:slug>/clients/<uuid:pk>/archive/",
        ClientArchiveEndpoint.as_view(),
        name="atlante-client-archive",
    ),
    path(
        "workspaces/<str:slug>/clients/<uuid:pk>/restore/",
        ClientRestoreEndpoint.as_view(),
        name="atlante-client-restore",
    ),
    path(
        "workspaces/<str:slug>/clients/<uuid:pk>/projects/",
        ClientProjectsEndpoint.as_view(),
        name="atlante-client-projects",
    ),
    path(
        "workspaces/<str:slug>/clients/<uuid:pk>/issues/",
        ClientIssuesEndpoint.as_view(),
        name="atlante-client-issues",
    ),
    path("workspaces/<str:slug>/project-clients/", ProjectClientMapEndpoint.as_view(), name="atlante-project-clients"),
    path("workspaces/<str:slug>/project-code/", ProjectCodeEndpoint.as_view(), name="atlante-project-code"),
    path("workspaces/<str:slug>/da-assegnare/", HomeTasksEndpoint.as_view(), name="atlante-home-tasks"),
    path("workspaces/<str:slug>/modelli/", TemplatesEndpoint.as_view(), name="atlante-templates"),
    path("errori/", BrowserErrorEndpoint.as_view(), name="atlante-browser-errors"),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/client/",
        ProjectClientEndpoint.as_view(),
        name="atlante-project-client",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/client/",
        IssueClientEndpoint.as_view(),
        name="atlante-issue-client",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/modello/",
        ProjectTemplateEndpoint.as_view(),
        name="atlante-project-template",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/ruoli/",
        ProjectRolesEndpoint.as_view(),
        name="atlante-project-roles",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/scelte/",
        TaskChoicesEndpoint.as_view(),
        name="atlante-task-choices",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/approvazione/",
        TaskApprovalEndpoint.as_view(),
        name="atlante-task-approval",
    ),
]
