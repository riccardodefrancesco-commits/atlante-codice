# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Invented people, workspaces and projects for Atlante's tests."""

import secrets
from types import SimpleNamespace
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from plane.atlante.models import PhaseBinding, ProjectRole
from plane.atlante.phases import apply_template
from plane.db.models import Issue, IssueAssignee, Project, ProjectMember, State, User, Workspace, WorkspaceMember
from plane.db.models.state import DEFAULT_STATES
from plane.license.models import Instance

ADMIN, MEMBER, GUEST = 20, 15, 5


def make_user(handle):
    user = User.objects.create(email=f"{handle}@esempio.it", username=f"u-{handle}", first_name=handle.capitalize())
    user.set_password("password-di-prova")
    user.save()
    return user


def make_project(workspace, identifier, members):
    """members: list of (user, project role)."""
    project = Project.objects.create(workspace=workspace, name=f"Progetto {identifier}", identifier=identifier)
    for user, role in members:
        ProjectMember.objects.create(project=project, member=user, role=role, workspace=workspace)
    states = State.objects.bulk_create(
        [
            State(
                name=state["name"],
                color=state["color"],
                project=project,
                workspace=workspace,
                sequence=state["sequence"],
                group=state["group"],
                default=state.get("default", False),
            )
            for state in DEFAULT_STATES
        ]
    )
    return project, {state.group: state for state in states}


def make_issue(project, state, target_date=None, name="Lavoro inventato"):
    return Issue.objects.create(
        project=project, workspace=project.workspace, name=name, state=state, target_date=target_date
    )


def logged_in(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def team(db):
    people = {handle: make_user(handle) for handle in ("admin", "membro", "ospite", "estraneo")}
    workspace = Workspace.objects.create(name="Spazio Prova", slug="spazio-prova", owner=people["admin"])
    for handle, role in (("admin", ADMIN), ("membro", MEMBER), ("ospite", GUEST)):
        WorkspaceMember.objects.create(workspace=workspace, member=people[handle], role=role)
    other = Workspace.objects.create(name="Altro spazio", slug="altro-spazio", owner=people["estraneo"])
    WorkspaceMember.objects.create(workspace=other, member=people["estraneo"], role=ADMIN)
    return SimpleNamespace(ws=workspace, other=other, base="/api/atlante/workspaces/spazio-prova", **people)


# The Video template (assaggio B and F): a project with invented people in every role.


@pytest.fixture(autouse=True)
def _no_background_tasks():
    """Plane's views send history and notifications to the worker: not needed here."""
    with (
        mock.patch("plane.app.views.issue.base.issue_activity"),
        mock.patch("plane.app.views.issue.base.model_activity"),
        mock.patch("plane.app.views.issue.base.issue_description_version_task"),
        mock.patch("plane.app.views.issue.base.recent_visited_task"),
        mock.patch("plane.app.views.issue.base.base_host", return_value="http://testserver"),
    ):
        yield


@pytest.fixture
def video(team):
    """A Video project with invented people in every role."""
    people = {handle: make_user(handle) for handle in ("davide", "giulia", "daniele", "virginia", "edoardo", "rick")}
    for person in people.values():
        WorkspaceMember.objects.create(workspace=team.ws, member=person, role=MEMBER)
    members = [(team.admin, ADMIN), (team.membro, MEMBER), (team.ospite, GUEST)]
    members += [(person, MEMBER) for person in people.values()]
    project, _ = make_project(team.ws, "DLTV", members)
    apply_template(project, "video")
    roles = {
        "account": ["davide"],
        "social_media_manager": ["giulia"],
        "lead_videomaker": ["daniele"],
        "videomaker": ["daniele", "virginia"],
        "editor": ["virginia"],
        "revisore_interno": ["giulia", "rick"],
        "grafico": ["edoardo"],
    }
    for role, handles in roles.items():
        for handle in handles:
            ProjectRole.objects.create(project=project, role=role, member=people[handle])
    states = {b.phase: b.state for b in PhaseBinding.objects.filter(project=project).select_related("state")}
    base = f"/api/workspaces/spazio-prova/projects/{project.id}"
    return SimpleNamespace(
        project=project, states=states, base=base, atlante=f"{team.base}/projects/{project.id}", **people
    )


def executors(issue):
    return set(IssueAssignee.objects.filter(issue=issue).values_list("assignee_id", flat=True))


def move(client, video, issue, phase):
    response = client.patch(
        f"{video.base}/issues/{issue.id}/", {"state_id": str(video.states[phase].id)}, format="json"
    )
    assert response.status_code == 204, response.content
    return Issue.objects.get(pk=issue.pk)


def create(client, video, **data):
    response = client.post(f"{video.base}/issues/", {"name": "Reel di ottobre", **data}, format="json")
    assert response.status_code == 201, response.content
    return Issue.objects.get(pk=response.data["id"]), response.data


# The online trial (zeta3-progetti, docs/collaudo-0.3.md): the local file with the four people.

PEOPLE_FILE = """# Credenziali di prova

## Zeta3 Prova

| Chi | Password |
| --- | --- |
| admin | non-va-letta |

## Zeta3 Collaudo

| Chi | Nome | Email | Password |
| --- | --- | --- | --- |
| rick | Rick | rick@lavoro.esempio.it | `password-rick-di-prova` |
| alessandra | Alessandra | alessandra@lavoro.esempio.it | `password-alessandra-prova` |
| virginia | Virginia | virginia@lavoro.esempio.it | `password-virginia-prova` |
| giulia | Giulia | giulia@lavoro.esempio.it | `password-giulia-di-prova` |
"""


@pytest.fixture
def instance(db):
    return Instance.objects.create(
        instance_name="Atlante prova",
        instance_id=secrets.token_hex(12),
        current_version="1.0.0",
        latest_version="1.0.0",
        last_checked_at=timezone.now(),
    )


@pytest.fixture
def people_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLANTE_AMBIENTE", "prova")
    path = tmp_path / "credenziali-prova.md"
    path.write_text(PEOPLE_FILE, encoding="utf-8")
    return str(path)
