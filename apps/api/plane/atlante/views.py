# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Client endpoints: the same rules for the Atlante interface (session login)
and for the public API (personal API key), written once in the *Handlers classes.

Rules (decided with Rick for the trial):
- workspace admins create, edit, archive and restore clients;
- workspace members see clients; guests never do;
- there is no "delete": clients are archived;
- a project has at most one client; only its admins link it;
- a work item has its own client only in projects without a client.
"""

import logging
import re

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.api.views.base import BaseAPIView as PublicBaseAPIView
from plane.app.views.base import BaseAPIView
from plane.atlante.models import Client, IssueClient, ProjectClient
from plane.atlante.project_names import suggest_code
from plane.atlante.error_codes import ALPHABET as CODE_ALPHABET, LENGTH as CODE_LENGTH, PREFIX as CODE_PREFIX
from plane.atlante.serializers import ClientSerializer
from plane.atlante.services import (
    client_issues,
    client_projects,
    client_stats,
    effective_client_id,
    record_client_activity,
)
from plane.db.models import Issue, Project, Workspace

NOT_FOUND = {"error": "Cliente non trovato."}


def _client_or_none(slug, pk):
    return Client.objects.filter(workspace__slug=slug, pk=pk).first()


def _with_stats(data, stats):
    row = stats.get(data["id"]) or stats.get(str(data["id"])) or {}
    return {**data, "project_count": 0, "open_issues": 0, "overdue_issues": 0, **row}


class ClientHandlers:
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        clients = Client.objects.filter(workspace=workspace)
        if request.GET.get("archived") == "true":
            clients = clients.filter(archived_at__isnull=False)
        elif request.GET.get("archived") != "all":
            clients = clients.filter(archived_at__isnull=True)
        search = request.GET.get("search", "").strip()
        if search:
            clients = clients.filter(name__icontains=search)
        stats = {str(k): v for k, v in client_stats(workspace).items()}
        data = [_with_stats(row, stats) for row in ClientSerializer(clients, many=True).data]
        return Response(data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        serializer = ClientSerializer(data=request.data, context={"workspace": workspace})
        if serializer.is_valid():
            serializer.save(workspace=workspace)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClientDetailHandlers:
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug, pk):
        client = _client_or_none(slug, pk)
        if client is None:
            return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        stats = {str(k): v for k, v in client_stats(client.workspace).items()}
        return Response(_with_stats(ClientSerializer(client).data, stats), status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def patch(self, request, slug, pk):
        client = _client_or_none(slug, pk)
        if client is None:
            return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        serializer = ClientSerializer(client, data=request.data, partial=True, context={"workspace": client.workspace})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClientArchiveHandlers:
    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug, pk):
        client = _client_or_none(slug, pk)
        if client is None:
            return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        if client.archived_at is None:
            client.archived_at = timezone.now()
            client.save(update_fields=["archived_at", "updated_at", "updated_by"])
        return Response(ClientSerializer(client).data, status=status.HTTP_200_OK)


class ClientRestoreHandlers:
    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug, pk):
        client = _client_or_none(slug, pk)
        if client is None:
            return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        if client.archived_at is not None:
            client.archived_at = None
            client.save(update_fields=["archived_at", "updated_at", "updated_by"])
        return Response(ClientSerializer(client).data, status=status.HTTP_200_OK)


class ClientProjectsHandlers:
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug, pk):
        client = _client_or_none(slug, pk)
        if client is None:
            return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        return Response(client_projects(client.workspace, client), status=status.HTTP_200_OK)


class ClientIssuesHandlers:
    """The work items of a client that the person may see, with counts by phase group."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug, pk):
        client = _client_or_none(slug, pk)
        if client is None:
            return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        return Response(client_issues(client.workspace, client, request.user), status=status.HTTP_200_OK)


class ProjectClientMapHandlers:
    """The "project -> client" map that the interface keeps in memory."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        links = ProjectClient.objects.filter(workspace__slug=slug, project__deleted_at__isnull=True)
        data = [{"project_id": str(p), "client_id": str(c)} for p, c in links.values_list("project_id", "client_id")]
        return Response(data, status=status.HTTP_200_OK)


class ProjectClientHandlers:
    """Link or unlink the client of a project: PUT {"client_id": "<id>" | null}."""

    @allow_permission([ROLE.ADMIN], level="PROJECT")
    def put(self, request, slug, project_id):
        project = Project.objects.filter(workspace__slug=slug, pk=project_id).first()
        if project is None:
            return Response({"error": "Progetto non trovato."}, status=status.HTTP_404_NOT_FOUND)
        if "client_id" not in request.data:
            return Response({"error": "Indica client_id (oppure null per scollegare)."}, status=status.HTTP_400_BAD_REQUEST)
        client_id = request.data.get("client_id")
        with transaction.atomic():
            link = ProjectClient.objects.select_for_update().filter(project=project).first()
            if client_id is None:
                if link is not None:
                    link.delete()  # only the link row: the client and the project stay
                return Response({"project_id": str(project.id), "client_id": None}, status=status.HTTP_200_OK)
            client = _client_or_none(slug, client_id)
            if client is None:
                return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
            if client.archived_at is not None:
                return Response(
                    {"error": "Il cliente è archiviato: ripristinalo prima di collegarlo a un progetto."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if IssueClient.objects.filter(project=project).exists():
                return Response(
                    {"error": "In questo progetto alcuni lavori hanno già un cliente proprio: toglilo prima."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if link is None:
                link = ProjectClient(project=project, workspace=project.workspace)
            link.client = client
            link.save()
        return Response({"project_id": str(project.id), "client_id": str(client.id)}, status=status.HTTP_200_OK)


class IssueClientHandlers:
    """Read the effective client of a work item; set its own client, only in
    projects without a client."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="PROJECT")
    def get(self, request, slug, project_id, issue_id):
        issue = Issue.issue_objects.filter(workspace__slug=slug, project_id=project_id, pk=issue_id).first()
        if issue is None:
            return Response({"error": "Lavoro non trovato."}, status=status.HTTP_404_NOT_FOUND)
        own = IssueClient.objects.filter(issue=issue).values_list("client_id", flat=True).first()
        client_id = effective_client_id(issue)
        return Response(
            {
                "issue_id": str(issue.id),
                "client_id": str(client_id) if client_id else None,
                "source": "issue" if own else ("project" if client_id else None),
                "editable": not ProjectClient.objects.filter(project_id=project_id).exists(),
            },
            status=status.HTTP_200_OK,
        )

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def put(self, request, slug, project_id, issue_id):
        issue = Issue.issue_objects.filter(workspace__slug=slug, project_id=project_id, pk=issue_id).first()
        if issue is None:
            return Response({"error": "Lavoro non trovato."}, status=status.HTTP_404_NOT_FOUND)
        if ProjectClient.objects.filter(project_id=project_id).exists():
            return Response(
                {"error": "Il progetto ha già un cliente: i suoi lavori hanno quello."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if "client_id" not in request.data:
            return Response({"error": "Indica client_id (oppure null per togliere il cliente)."}, status=status.HTTP_400_BAD_REQUEST)
        client_id = request.data.get("client_id")
        with transaction.atomic():
            link = IssueClient.objects.select_for_update().filter(issue=issue).select_related("client").first()
            old_client = link.client if link is not None else None
            if client_id is None:
                if link is not None:
                    link.delete()  # only the link row
                    record_client_activity(issue, request.user, old_client, None)
                return Response({"issue_id": str(issue.id), "client_id": None}, status=status.HTTP_200_OK)
            client = _client_or_none(slug, client_id)
            if client is None:
                return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
            if client.archived_at is not None:
                return Response({"error": "Il cliente è archiviato."}, status=status.HTTP_400_BAD_REQUEST)
            if link is None:
                link = IssueClient(issue=issue, project_id=issue.project_id, workspace_id=issue.workspace_id)
            link.client = client
            link.save()
            if old_client is None or old_client.pk != client.pk:
                record_client_activity(issue, request.user, old_client, client)
        return Response({"issue_id": str(issue.id), "client_id": str(client.id)}, status=status.HTTP_200_OK)


# Interface endpoints (session login), under /api/atlante/


class ClientEndpoint(ClientHandlers, BaseAPIView):
    pass


class ClientDetailEndpoint(ClientDetailHandlers, BaseAPIView):
    pass


class ClientArchiveEndpoint(ClientArchiveHandlers, BaseAPIView):
    pass


class ClientRestoreEndpoint(ClientRestoreHandlers, BaseAPIView):
    pass


class ClientProjectsEndpoint(ClientProjectsHandlers, BaseAPIView):
    pass


class ClientIssuesEndpoint(ClientIssuesHandlers, BaseAPIView):
    pass


class ProjectClientMapEndpoint(ProjectClientMapHandlers, BaseAPIView):
    pass


class ProjectClientEndpoint(ProjectClientHandlers, BaseAPIView):
    pass


class IssueClientEndpoint(IssueClientHandlers, BaseAPIView):
    pass


class ProjectCodeEndpoint(BaseAPIView):
    """The code Atlante proposes for a new project with this name (zeta3-progetti#18)."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        name = request.GET.get("name", "").strip()
        if not name:
            return Response({"error": "Indica il nome del progetto."}, status=status.HTTP_400_BAD_REQUEST)
        workspace = Workspace.objects.get(slug=slug)
        return Response({"code": suggest_code(workspace.id, name)}, status=status.HTTP_200_OK)


BROWSER_CODE = re.compile(rf"{CODE_PREFIX}[{CODE_ALPHABET}]{{{CODE_LENGTH}}}")
# At most this many browser errors per person per minute: a broken page must not flood the log.
BROWSER_ERRORS_PER_MINUTE = 20


class BrowserErrorEndpoint(BaseAPIView):
    """A page that breaks in the browser shows a code and sends it here, so the code is in the log
    with page, browser and the person's id (docs/proposta-codici-errore.md). Only signed-in people;
    the error's own text is never sent, because it could contain data."""

    def post(self, request):
        code = str(request.data.get("codice", ""))
        if not BROWSER_CODE.fullmatch(code):
            return Response({"error": "Codice non valido."}, status=status.HTTP_400_BAD_REQUEST)
        counter = f"atlante-errori-browser-{request.user.id}"
        if cache.get_or_set(counter, 0, 60) >= BROWSER_ERRORS_PER_MINUTE:
            return Response(status=status.HTTP_429_TOO_MANY_REQUESTS)
        cache.incr(counter)
        logging.getLogger("plane.exception").error(
            "Errore nel browser",
            extra={
                "codice": code,
                "path": str(request.data.get("pagina", ""))[:200],
                "method": "BROWSER",
                "user_id": str(request.user.id),
                "tipo": str(request.data.get("tipo", ""))[:80],
                "browser": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# Public API endpoints (personal API key, Plane's rate limit), under /api/v1/atlante/


class PublicClientEndpoint(ClientHandlers, PublicBaseAPIView):
    pass


class PublicClientDetailEndpoint(ClientDetailHandlers, PublicBaseAPIView):
    pass


class PublicClientArchiveEndpoint(ClientArchiveHandlers, PublicBaseAPIView):
    pass


class PublicClientRestoreEndpoint(ClientRestoreHandlers, PublicBaseAPIView):
    pass


class PublicClientIssuesEndpoint(ClientIssuesHandlers, PublicBaseAPIView):
    pass


class PublicProjectClientEndpoint(ProjectClientHandlers, PublicBaseAPIView):
    pass
