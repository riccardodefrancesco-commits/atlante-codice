# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The agency board: the workspace's "all work items" with groups (columns by phase,
rows by client), with exactly Plane's rules on who sees what."""

import pytest

from plane.atlante.tests.conftest import ADMIN, logged_in, make_issue, make_project
from plane.atlante.tests.test_cliente_nei_lavori import agency, names  # noqa: F401 (agency is a fixture)

pytestmark = [pytest.mark.contract, pytest.mark.django_db]


def all_items_url(team, **params):
    query = "&".join(f"{key}={value}" for key, value in params.items())
    return f"/api/workspaces/{team.ws.slug}/issues/" + (f"?{query}" if query else "")


def test_the_table_is_plane_s_with_the_client_added(agency):
    team = agency.team
    response = logged_in(team.admin).get(all_items_url(team))

    assert response.status_code == 200
    clients = {issue["name"]: issue["atlante_client_id"] for issue in response.data["results"]}
    assert clients == {
        "Post di Alfa": str(agency.alfa.id),
        "Reel di Alfa": str(agency.alfa.id),
        "Video per Alfa": str(agency.alfa.id),
        "Video per Beta": str(agency.beta.id),
        "Video interno": None,
    }


def test_board_columns_by_phase_and_rows_by_client(agency):
    team = agency.team
    response = logged_in(team.admin).get(
        all_items_url(team, group_by="state__group", sub_group_by="atlante_client_id")
    )

    assert response.status_code == 200, response.data
    columns = response.data["results"]
    not_started = columns["unstarted"]["results"]
    assert names(not_started[str(agency.alfa.id)]["results"]) == ["Post di Alfa", "Video per Alfa"]
    assert names(not_started[str(agency.beta.id)]["results"]) == ["Video per Beta"]
    assert names(not_started["None"]["results"]) == ["Video interno"]
    assert names(columns["started"]["results"][str(agency.alfa.id)]["results"]) == ["Reel di Alfa"]


def test_list_grouped_by_client_across_projects(agency):
    team = agency.team
    groups = logged_in(team.admin).get(all_items_url(team, group_by="atlante_client_id")).data["results"]

    assert names(groups[str(agency.alfa.id)]["results"]) == ["Post di Alfa", "Reel di Alfa", "Video per Alfa"]
    assert names(groups["None"]["results"]) == ["Video interno"]


def test_only_projects_the_person_belongs_to(agency):
    team = agency.team
    secret, states = make_project(team.ws, "SEGR", [(team.admin, ADMIN)])
    make_issue(secret, states["unstarted"], name="Lavoro riservato")

    member = logged_in(team.membro)
    plain = names(member.get(all_items_url(team)).data["results"])
    grouped = member.get(all_items_url(team, group_by="atlante_client_id")).data["results"]

    assert "Lavoro riservato" not in plain
    assert "Lavoro riservato" not in [name for group in grouped.values() for name in names(group["results"])]
    assert "Lavoro riservato" in names(logged_in(team.admin).get(all_items_url(team)).data["results"])


def test_guests_see_exactly_what_they_saw_before(agency):
    team = agency.team
    guest = logged_in(team.ospite)

    plain = names(guest.get(all_items_url(team)).data["results"])
    grouped = guest.get(all_items_url(team, group_by="state__group")).data["results"]

    assert [name for group in grouped.values() for name in names(group["results"])] == plain


def test_same_group_twice_and_unknown_groups_are_refused(agency):
    team = agency.team
    admin = logged_in(team.admin)

    assert admin.get(all_items_url(team, group_by="priority", sub_group_by="priority")).status_code == 400
    assert admin.get(all_items_url(team, group_by="name")).status_code == 400
