# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The client inside Plane's work item lists, filters, history and public API."""

import json
from types import SimpleNamespace

import pytest
from rest_framework.test import APIClient

from plane.atlante.models import Client, IssueClient, ProjectClient
from plane.atlante.tests.conftest import ADMIN, GUEST, MEMBER, logged_in, make_issue, make_project
from plane.db.models import APIToken, IssueActivity

pytestmark = [pytest.mark.contract, pytest.mark.django_db]


@pytest.fixture
def agency(team):
    """ALFA belongs to Alfa; VIDEO has no client, its items have their own."""
    alfa = Client.objects.create(workspace=team.ws, name="Alfa Biscotti", code="ALF")
    beta = Client.objects.create(workspace=team.ws, name="Beta Moda", code="BET")
    alfa_project, alfa_states = make_project(team.ws, "ALFA", [(team.admin, ADMIN), (team.membro, MEMBER)])
    ProjectClient.objects.create(project=alfa_project, client=alfa, workspace=team.ws)
    post = make_issue(alfa_project, alfa_states["unstarted"], name="Post di Alfa")
    reel = make_issue(alfa_project, alfa_states["started"], name="Reel di Alfa")

    video, video_states = make_project(
        team.ws, "VIDEO", [(team.admin, ADMIN), (team.membro, MEMBER), (team.ospite, GUEST)]
    )
    video_alfa = make_issue(video, video_states["unstarted"], name="Video per Alfa")
    video_beta = make_issue(video, video_states["unstarted"], name="Video per Beta")
    video_none = make_issue(video, video_states["unstarted"], name="Video interno")
    IssueClient.objects.create(issue=video_alfa, client=alfa, project=video, workspace=team.ws)
    IssueClient.objects.create(issue=video_beta, client=beta, project=video, workspace=team.ws)
    return SimpleNamespace(
        team=team,
        alfa=alfa,
        beta=beta,
        alfa_project=alfa_project,
        video=video,
        post=post,
        reel=reel,
        video_alfa=video_alfa,
        video_beta=video_beta,
        video_none=video_none,
    )


def issues_url(team, project, **params):
    query = "&".join(f"{key}={value}" for key, value in params.items())
    return f"/api/workspaces/{team.ws.slug}/projects/{project.id}/issues/" + (f"?{query}" if query else "")


def names(results):
    return sorted(issue["name"] for issue in results)


# Lists


def test_every_listed_item_carries_its_effective_client(agency):
    team = agency.team
    admin = logged_in(team.admin)
    alfa_items = admin.get(issues_url(team, agency.alfa_project)).data["results"]
    assert {i["atlante_client_id"] for i in alfa_items} == {agency.alfa.id}

    video_items = {i["name"]: i["atlante_client_id"] for i in admin.get(issues_url(team, agency.video)).data["results"]}
    assert video_items == {
        "Video per Alfa": agency.alfa.id,
        "Video per Beta": agency.beta.id,
        "Video interno": None,
    }


def test_group_by_client(agency):
    team = agency.team
    response = logged_in(team.admin).get(issues_url(team, agency.video, group_by="atlante_client_id"))
    assert response.status_code == 200, response.data
    groups = response.data["results"]
    assert names(groups[str(agency.alfa.id)]["results"]) == ["Video per Alfa"]
    assert names(groups[str(agency.beta.id)]["results"]) == ["Video per Beta"]
    assert names(groups["None"]["results"]) == ["Video interno"]
    assert groups[str(agency.alfa.id)]["total_results"] == 1


def test_sub_group_by_client_rows_on_the_board(agency):
    team = agency.team
    response = logged_in(team.admin).get(
        issues_url(team, agency.video, group_by="state_id", sub_group_by="atlante_client_id")
    )
    assert response.status_code == 200, response.data
    columns = response.data["results"]
    unstarted = next(column for column in columns.values() if column["results"])
    rows = unstarted["results"]
    assert names(rows[str(agency.beta.id)]["results"]) == ["Video per Beta"]
    assert names(rows["None"]["results"]) == ["Video interno"]


def test_existing_groupings_still_work(agency):
    team = agency.team
    admin = logged_in(team.admin)
    for group_by in ("state_id", "priority", "assignees__id", "labels__id"):
        response = admin.get(issues_url(team, agency.alfa_project, group_by=group_by))
        assert response.status_code == 200, (group_by, response.data)


# Filters


@pytest.mark.parametrize(
    "condition, expected",
    [
        ("client", ["Video per Alfa"]),
        ("clients", ["Video per Alfa", "Video per Beta"]),
        ("no_client", ["Video interno"]),
        ("with_client", ["Video per Alfa", "Video per Beta"]),
    ],
)
def test_filter_by_client(agency, condition, expected):
    team = agency.team
    filters = {
        "client": {"client_id": str(agency.alfa.id)},
        "clients": {"client_id__in": f"{agency.alfa.id},{agency.beta.id}"},
        "no_client": {"client_id__isnull": True},
        "with_client": {"client_id__isnull": False},
    }[condition]
    response = logged_in(team.admin).get(issues_url(team, agency.video, filters=json.dumps(filters)))
    assert response.status_code == 200, response.data
    assert names(response.data["results"]) == expected


def test_filter_uses_the_project_client(agency):
    team = agency.team
    filters = json.dumps({"client_id": str(agency.alfa.id)})
    response = logged_in(team.admin).get(issues_url(team, agency.alfa_project, filters=filters))
    assert names(response.data["results"]) == ["Post di Alfa", "Reel di Alfa"]


def test_guests_see_exactly_what_they_saw_before(agency):
    """A guest still sees only the items they created (Plane's rule), with or without client grouping."""
    team = agency.team
    own = make_issue(agency.video, agency.video_alfa.state, name="Richiesta dell'ospite")
    own.created_by = team.ospite
    own.save(created_by_id=team.ospite.id)
    guest = logged_in(team.ospite)
    plain = guest.get(issues_url(team, agency.video)).data["results"]
    grouped = guest.get(issues_url(team, agency.video, group_by="atlante_client_id")).data["results"]
    assert names(plain) == ["Richiesta dell'ospite"]
    assert [name for group in grouped.values() for name in names(group["results"])] == ["Richiesta dell'ospite"]


# Reading the client of one item, and the history


def test_read_the_client_of_one_item(agency):
    team = agency.team
    member = logged_in(team.membro)
    of_project = member.get(
        f"{team.base}/projects/{agency.alfa_project.id}/issues/{agency.post.id}/client/"
    ).data
    assert (of_project["client_id"], of_project["source"], of_project["editable"]) == (
        str(agency.alfa.id),
        "project",
        False,
    )
    own = member.get(f"{team.base}/projects/{agency.video.id}/issues/{agency.video_beta.id}/client/").data
    assert (own["client_id"], own["source"], own["editable"]) == (str(agency.beta.id), "issue", True)
    none = member.get(f"{team.base}/projects/{agency.video.id}/issues/{agency.video_none.id}/client/").data
    assert (none["client_id"], none["source"]) == (None, None)


def test_changing_the_client_writes_the_history(agency):
    team = agency.team
    member = logged_in(team.membro)
    url = f"{team.base}/projects/{agency.video.id}/issues/{agency.video_none.id}/client/"

    member.put(url, {"client_id": str(agency.alfa.id)}, format="json")
    member.put(url, {"client_id": str(agency.alfa.id)}, format="json")  # same client: no new line
    member.put(url, {"client_id": str(agency.beta.id)}, format="json")
    member.put(url, {"client_id": None}, format="json")

    history = list(
        IssueActivity.objects.filter(issue=agency.video_none, field="atlante_client")
        .order_by("created_at")
        .values_list("old_value", "new_value", "actor__email")
    )
    assert history == [
        (None, "Alfa Biscotti", "membro@esempio.it"),
        ("Alfa Biscotti", "Beta Moda", "membro@esempio.it"),
        ("Beta Moda", None, "membro@esempio.it"),
    ]


# Public API with a personal key


def key_client(user, token):
    APIToken.objects.create(user=user, label="Chiave di prova", token=token)
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=token)
    return client


def test_public_api_reads_and_creates_clients(agency):
    team = agency.team
    base = f"/api/v1/atlante/workspaces/{team.ws.slug}"
    admin = key_client(team.admin, "plane_api_chiave-admin-di-prova")
    listed = admin.get(f"{base}/clients/")
    assert listed.status_code == 200
    assert [c["code"] for c in listed.data] == ["ALF", "BET"]
    created = admin.post(f"{base}/clients/", {"name": "Gamma Palestre", "code": "GAM"}, format="json")
    assert created.status_code == 201
    assert admin.post(f"{base}/clients/{created.data['id']}/archive/").status_code == 200
    assert admin.delete(f"{base}/clients/{created.data['id']}/").status_code == 405


def test_public_api_keeps_the_same_rules(agency):
    team = agency.team
    base = f"/api/v1/atlante/workspaces/{team.ws.slug}"
    member = key_client(team.membro, "plane_api_chiave-membro-di-prova")
    assert member.get(f"{base}/clients/").status_code == 200
    assert member.post(f"{base}/clients/", {"name": "Delta", "code": "DEL"}, format="json").status_code == 403
    guest = key_client(team.ospite, "plane_api_chiave-ospite-di-prova")
    assert guest.get(f"{base}/clients/").status_code == 403


def test_public_api_needs_a_valid_key(agency):
    team = agency.team
    nobody = APIClient()
    nobody.credentials(HTTP_X_API_KEY="plane_api_chiave-inventata-che-non-esiste")
    # Plane answers 401 or 403 when the key is missing or wrong: never the data.
    assert nobody.get(f"/api/v1/atlante/workspaces/{team.ws.slug}/clients/").status_code in (401, 403)
    assert APIClient().get(f"/api/v1/atlante/workspaces/{team.ws.slug}/clients/").status_code in (401, 403)


# Ordering the table by client name


def test_order_by_client_name(agency):
    team = agency.team
    admin = logged_in(team.admin)
    ascending = admin.get(issues_url(team, agency.video, order_by="atlante_client__name")).data["results"]
    assert [i["name"] for i in ascending] == ["Video per Alfa", "Video per Beta", "Video interno"]
    descending = admin.get(issues_url(team, agency.video, order_by="-atlante_client__name")).data["results"]
    assert [i["name"] for i in descending] == ["Video per Beta", "Video per Alfa", "Video interno"]


def test_order_by_client_name_inside_groups(agency):
    team = agency.team
    response = logged_in(team.admin).get(
        issues_url(team, agency.video, group_by="state_id", order_by="atlante_client__name")
    )
    assert response.status_code == 200, response.data
    column = next(group for group in response.data["results"].values() if group["results"])
    assert [i["name"] for i in column["results"]] == ["Video per Alfa", "Video per Beta", "Video interno"]


def test_plane_orderings_still_work(agency):
    team = agency.team
    admin = logged_in(team.admin)
    for order_by in ("-priority", "state__name", "-created_at", "target_date", "labels__name"):
        assert admin.get(issues_url(team, agency.video, order_by=order_by)).status_code == 200, order_by


def test_load_more_of_one_client_group(agency):
    """Plane's interface loads more items of a group with a legacy filter: atlante_client=<id> or None."""
    team = agency.team
    admin = logged_in(team.admin)
    alfa = admin.get(issues_url(team, agency.video, atlante_client=str(agency.alfa.id))).data["results"]
    assert names(alfa) == ["Video per Alfa"]
    none = admin.get(issues_url(team, agency.video, atlante_client="None")).data["results"]
    assert names(none) == ["Video interno"]
    of_project = admin.get(issues_url(team, agency.alfa_project, atlante_client=str(agency.alfa.id))).data["results"]
    assert names(of_project) == ["Post di Alfa", "Reel di Alfa"]
