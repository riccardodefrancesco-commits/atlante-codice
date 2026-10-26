# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Clients: who can do what, and the rules decided with Rick."""

from datetime import timedelta

import pytest
from django.utils import timezone

from plane.atlante.models import Client, IssueClient, ProjectClient
from plane.atlante.services import workspace_today
from plane.atlante.tests.conftest import ADMIN, GUEST, MEMBER, logged_in, make_issue, make_project
from plane.db.models import Issue, Project

pytestmark = [pytest.mark.contract, pytest.mark.django_db]


def new_client(workspace, name="Alfa Biscotti", code="ALF"):
    return Client.objects.create(workspace=workspace, name=name, code=code)


# Creating and seeing clients


def test_admin_creates_a_client(team):
    response = logged_in(team.admin).post(
        f"{team.base}/clients/", {"name": " Alfa Biscotti ", "code": "alf", "color": "#e5484d"}, format="json"
    )
    assert response.status_code == 201, response.data
    assert response.data["name"] == "Alfa Biscotti"
    assert response.data["code"] == "ALF"
    assert response.data["color"] == "#E5484D"
    assert Client.objects.get().created_by == team.admin


@pytest.mark.parametrize("who", ["membro", "ospite", "estraneo"])
def test_only_admins_create_clients(team, who):
    response = logged_in(getattr(team, who)).post(f"{team.base}/clients/", {"name": "Beta", "code": "BET"}, format="json")
    assert response.status_code == 403
    assert not Client.objects.exists()


def test_members_see_clients_guests_never(team):
    client = new_client(team.ws)
    member = logged_in(team.membro)
    assert member.get(f"{team.base}/clients/").status_code == 200
    assert [c["name"] for c in member.get(f"{team.base}/clients/").data] == ["Alfa Biscotti"]
    assert member.get(f"{team.base}/clients/{client.id}/").status_code == 200

    guest = logged_in(team.ospite)
    assert guest.get(f"{team.base}/clients/").status_code == 403
    assert guest.get(f"{team.base}/clients/{client.id}/").status_code == 403
    assert guest.get(f"{team.base}/project-clients/").status_code == 403


def test_clients_of_another_workspace_are_never_visible(team):
    foreign = new_client(team.other, name="Cliente altrui", code="ALT")
    admin = logged_in(team.admin)
    assert admin.get(f"{team.base}/clients/").data == []
    assert admin.get(f"{team.base}/clients/{foreign.id}/").status_code == 404
    assert admin.patch(f"{team.base}/clients/{foreign.id}/", {"name": "Preso"}, format="json").status_code == 404
    # Someone outside the workspace cannot even list it.
    assert logged_in(team.estraneo).get(f"{team.base}/clients/").status_code == 403


def test_name_and_code_are_unique_in_the_workspace(team):
    new_client(team.ws)
    admin = logged_in(team.admin)
    same_name = admin.post(f"{team.base}/clients/", {"name": "alfa biscotti", "code": "BET"}, format="json")
    assert same_name.status_code == 400 and "name" in same_name.data
    same_code = admin.post(f"{team.base}/clients/", {"name": "Beta Moda", "code": "alf"}, format="json")
    assert same_code.status_code == 400 and "code" in same_code.data
    beta = new_client(team.ws, name="Beta Moda", code="BET")
    rename = admin.patch(f"{team.base}/clients/{beta.id}/", {"name": "ALFA BISCOTTI"}, format="json")
    assert rename.status_code == 400
    # The same name is fine in another workspace.
    assert new_client(team.other).pk


def test_code_and_color_are_checked(team):
    admin = logged_in(team.admin)
    assert admin.post(f"{team.base}/clients/", {"name": "Gamma", "code": "GAM MA"}, format="json").status_code == 400
    assert admin.post(f"{team.base}/clients/", {"name": "Gamma", "code": "TROPPOLUNGA123"}, format="json").status_code == 400
    assert (
        admin.post(f"{team.base}/clients/", {"name": "Gamma", "code": "GAM", "color": "rosso"}, format="json").status_code
        == 400
    )


def test_internal_contact_must_be_a_team_member(team):
    admin = logged_in(team.admin)
    guest_contact = admin.post(
        f"{team.base}/clients/", {"name": "Delta", "code": "DEL", "internal_contact": str(team.ospite.id)}, format="json"
    )
    assert guest_contact.status_code == 400
    ok = admin.post(
        f"{team.base}/clients/", {"name": "Delta", "code": "DEL", "internal_contact": str(team.membro.id)}, format="json"
    )
    assert ok.status_code == 201
    assert str(ok.data["internal_contact"]) == str(team.membro.id)


# No delete: archive and restore


def test_there_is_no_delete(team):
    client = new_client(team.ws)
    response = logged_in(team.admin).delete(f"{team.base}/clients/{client.id}/")
    assert response.status_code == 405
    assert Client.objects.filter(pk=client.pk).exists()


def test_archive_does_not_touch_projects_and_work_items(team):
    client = new_client(team.ws)
    project, states = make_project(team.ws, "ALFA", [(team.admin, ADMIN)])
    ProjectClient.objects.create(project=project, client=client, workspace=team.ws)
    make_issue(project, states["started"])
    admin = logged_in(team.admin)

    archived = admin.post(f"{team.base}/clients/{client.id}/archive/")
    assert archived.status_code == 200 and archived.data["archived_at"] is not None
    assert ProjectClient.objects.filter(project=project, client=client).exists()
    assert Issue.issue_objects.filter(project=project).count() == 1
    assert Project.objects.filter(pk=project.pk, archived_at__isnull=True).exists()

    assert admin.get(f"{team.base}/clients/").data == []
    assert [c["code"] for c in admin.get(f"{team.base}/clients/?archived=true").data] == ["ALF"]

    restored = admin.post(f"{team.base}/clients/{client.id}/restore/")
    assert restored.status_code == 200 and restored.data["archived_at"] is None
    assert [c["code"] for c in admin.get(f"{team.base}/clients/").data] == ["ALF"]


def test_only_admins_archive(team):
    client = new_client(team.ws)
    assert logged_in(team.membro).post(f"{team.base}/clients/{client.id}/archive/").status_code == 403
    client.refresh_from_db()
    assert client.archived_at is None


# Projects and work items


def test_only_project_admins_link_a_client(team):
    client = new_client(team.ws)
    project, _ = make_project(team.ws, "ALFA", [(team.admin, ADMIN), (team.membro, MEMBER)])
    url = f"{team.base}/projects/{project.id}/client/"

    assert logged_in(team.membro).put(url, {"client_id": str(client.id)}, format="json").status_code == 403
    assert not ProjectClient.objects.exists()

    admin = logged_in(team.admin)
    assert admin.put(url, {"client_id": str(client.id)}, format="json").status_code == 200
    assert ProjectClient.objects.get(project=project).client == client

    # At most one client per project: a new one replaces the old one.
    beta = new_client(team.ws, name="Beta Moda", code="BET")
    assert admin.put(url, {"client_id": str(beta.id)}, format="json").status_code == 200
    assert list(ProjectClient.objects.filter(project=project).values_list("client__code", flat=True)) == ["BET"]

    # Unlinking removes only the link.
    assert admin.put(url, {"client_id": None}, format="json").status_code == 200
    assert not ProjectClient.objects.exists()
    assert Client.objects.count() == 2


def test_an_archived_client_cannot_be_linked(team):
    client = new_client(team.ws)
    client.archived_at = timezone.now()
    client.save()
    project, _ = make_project(team.ws, "ALFA", [(team.admin, ADMIN)])
    response = logged_in(team.admin).put(
        f"{team.base}/projects/{project.id}/client/", {"client_id": str(client.id)}, format="json"
    )
    assert response.status_code == 400
    assert not ProjectClient.objects.exists()


def test_work_item_client_only_in_projects_without_client(team):
    alfa, beta = new_client(team.ws), new_client(team.ws, name="Beta Moda", code="BET")
    video, video_states = make_project(
        team.ws, "VIDEO", [(team.admin, ADMIN), (team.membro, MEMBER), (team.ospite, GUEST)]
    )
    shoot = make_issue(video, video_states["unstarted"])
    url = f"{team.base}/projects/{video.id}/issues/{shoot.id}/client/"

    assert logged_in(team.membro).put(url, {"client_id": str(beta.id)}, format="json").status_code == 200
    assert IssueClient.objects.get(issue=shoot).client == beta
    assert logged_in(team.ospite).put(url, {"client_id": str(alfa.id)}, format="json").status_code == 403

    social, social_states = make_project(team.ws, "ALFA", [(team.admin, ADMIN), (team.membro, MEMBER)])
    ProjectClient.objects.create(project=social, client=alfa, workspace=team.ws)
    post = make_issue(social, social_states["unstarted"])
    refused = logged_in(team.membro).put(
        f"{team.base}/projects/{social.id}/issues/{post.id}/client/", {"client_id": str(beta.id)}, format="json"
    )
    assert refused.status_code == 400
    assert not IssueClient.objects.filter(issue=post).exists()


def test_project_with_own_work_item_clients_cannot_get_a_client(team):
    alfa = new_client(team.ws)
    video, states = make_project(team.ws, "VIDEO", [(team.admin, ADMIN)])
    shoot = make_issue(video, states["unstarted"])
    IssueClient.objects.create(issue=shoot, client=alfa, project=video, workspace=team.ws)
    response = logged_in(team.admin).put(
        f"{team.base}/projects/{video.id}/client/", {"client_id": str(alfa.id)}, format="json"
    )
    assert response.status_code == 400


# Numbers shown in the client list


def test_client_numbers(team):
    client = new_client(team.ws)
    today = workspace_today(team.ws)
    project, states = make_project(team.ws, "ALFA", [(team.admin, ADMIN)])
    ProjectClient.objects.create(project=project, client=client, workspace=team.ws)
    make_issue(project, states["completed"], target_date=today - timedelta(days=5))
    make_issue(project, states["started"], target_date=today - timedelta(days=1))
    make_issue(project, states["unstarted"], target_date=today + timedelta(days=3))
    video, video_states = make_project(team.ws, "VIDEO", [(team.admin, ADMIN)])
    shoot = make_issue(video, video_states["unstarted"])
    IssueClient.objects.create(issue=shoot, client=client, project=video, workspace=team.ws)

    row = logged_in(team.admin).get(f"{team.base}/clients/").data[0]
    assert (row["project_count"], row["open_issues"], row["overdue_issues"]) == (1, 3, 1)

    projects = logged_in(team.membro).get(f"{team.base}/clients/{client.id}/projects/")
    assert projects.status_code == 200
    assert [(p["identifier"], p["total_issues"], p["completed_issues"]) for p in projects.data] == [("ALFA", 3, 1)]


def test_deleted_projects_are_ignored(team):
    client = new_client(team.ws)
    project, _ = make_project(team.ws, "ALFA", [(team.admin, ADMIN)])
    ProjectClient.objects.create(project=project, client=client, workspace=team.ws)
    Project.all_objects.filter(pk=project.pk).update(deleted_at=timezone.now())  # Plane's soft delete

    admin = logged_in(team.admin)
    assert admin.get(f"{team.base}/clients/{client.id}/projects/").data == []
    assert admin.get(f"{team.base}/project-clients/").data == []
    assert admin.get(f"{team.base}/clients/").data[0]["project_count"] == 0
    assert Client.objects.filter(pk=client.pk).exists()


def test_project_client_map(team):
    client = new_client(team.ws)
    project, _ = make_project(team.ws, "ALFA", [(team.admin, ADMIN)])
    ProjectClient.objects.create(project=project, client=client, workspace=team.ws)
    other_project, _ = make_project(team.other, "ALT", [(team.estraneo, ADMIN)])
    ProjectClient.objects.create(
        project=other_project, client=new_client(team.other, code="ALT"), workspace=team.other
    )
    data = logged_in(team.membro).get(f"{team.base}/project-clients/").data
    assert data == [{"project_id": str(project.id), "client_id": str(client.id)}]
