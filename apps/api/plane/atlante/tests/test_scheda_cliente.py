# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The client card: the work items of a client, with Plane's visibility rules."""

from datetime import timedelta

import pytest

from plane.atlante.models import Client, IssueClient, ProjectClient
from plane.atlante.services import client_issues, workspace_today
from plane.atlante.tests.conftest import ADMIN, GUEST, MEMBER, logged_in, make_issue, make_project
from plane.db.models import Issue, Project

pytestmark = [pytest.mark.contract, pytest.mark.django_db]


def setup_alfa(team, video_members=None):
    """Alfa Biscotti with a project of its own and one item in Produzione video;
    Beta Moda with an item in Produzione video too."""
    alfa = Client.objects.create(workspace=team.ws, name="Alfa Biscotti", code="ALF")
    beta = Client.objects.create(workspace=team.ws, name="Beta Moda", code="BET")
    today = workspace_today(team.ws)
    project, states = make_project(team.ws, "ALFA", [(team.admin, ADMIN), (team.membro, MEMBER)])
    ProjectClient.objects.create(project=project, client=alfa, workspace=team.ws)
    done = make_issue(project, states["completed"], name="Logo consegnato")
    late = make_issue(project, states["started"], target_date=today - timedelta(days=2), name="Post in ritardo")
    todo = make_issue(project, states["unstarted"], target_date=today + timedelta(days=3), name="Piano editoriale")
    members = video_members if video_members is not None else [(team.admin, ADMIN), (team.membro, MEMBER)]
    video, video_states = make_project(team.ws, "VIDEO", members)
    shoot = make_issue(video, video_states["backlog"], name="Riprese Alfa")
    IssueClient.objects.create(issue=shoot, client=alfa, project=video, workspace=team.ws)
    other = make_issue(video, video_states["backlog"], name="Riprese Beta")
    IssueClient.objects.create(issue=other, client=beta, project=video, workspace=team.ws)
    return alfa, {"done": done, "late": late, "todo": todo, "shoot": shoot, "other": other}


def test_client_work_items_from_its_projects_and_own_items(team):
    alfa, items = setup_alfa(team)

    response = logged_in(team.membro).get(f"{team.base}/clients/{alfa.id}/issues/")

    assert response.status_code == 200
    data = response.data
    # to do first (backlog, then not started), then started, then completed
    assert [row["name"] for row in data["results"]] == [
        "Riprese Alfa",
        "Piano editoriale",
        "Post in ritardo",
        "Logo consegnato",
    ]
    assert data["counts"] == {"backlog": 1, "unstarted": 1, "started": 1, "completed": 1, "cancelled": 0}
    assert (data["total"], data["overdue"], data["truncated"]) == (4, 1, False)
    late = next(row for row in data["results"] if row["name"] == "Post in ritardo")
    assert (late["project_identifier"], late["overdue"], late["state_group"]) == ("ALFA", True, "started")


def test_only_projects_the_person_belongs_to(team):
    alfa, _ = setup_alfa(team, video_members=[(team.admin, ADMIN)])

    names = [row["name"] for row in logged_in(team.membro).get(f"{team.base}/clients/{alfa.id}/issues/").data["results"]]

    assert "Riprese Alfa" not in names
    assert len(names) == 3


def test_project_guest_sees_only_what_they_created(team):
    alfa, items = setup_alfa(team, video_members=[(team.admin, ADMIN), (team.membro, GUEST)])
    Issue.objects.filter(pk=items["shoot"].pk).update(created_by=team.membro)
    other_alfa = make_issue(items["shoot"].project, items["shoot"].state, name="Montaggio Alfa")
    IssueClient.objects.create(issue=other_alfa, client=alfa, project=items["shoot"].project, workspace=team.ws)

    names = [row["name"] for row in logged_in(team.membro).get(f"{team.base}/clients/{alfa.id}/issues/").data["results"]]

    assert "Riprese Alfa" in names
    assert "Montaggio Alfa" not in names

    Project.objects.filter(pk=items["shoot"].project_id).update(guest_view_all_features=True)
    names = [row["name"] for row in logged_in(team.membro).get(f"{team.base}/clients/{alfa.id}/issues/").data["results"]]
    assert "Montaggio Alfa" in names


def test_workspace_guests_never_see_client_work_items(team):
    alfa, _ = setup_alfa(team)

    assert logged_in(team.ospite).get(f"{team.base}/clients/{alfa.id}/issues/").status_code == 403


def test_list_is_limited_but_counts_are_complete(team):
    alfa, _ = setup_alfa(team)

    data = client_issues(team.ws, alfa, team.membro, limit=2)

    assert len(data["results"]) == 2
    assert (data["total"], data["truncated"]) == (4, True)


def test_client_of_another_workspace_is_not_found(team):
    foreign = Client.objects.create(workspace=team.other, name="Gamma Palestre", code="GAM")

    assert logged_in(team.admin).get(f"{team.base}/clients/{foreign.id}/issues/").status_code == 404
