# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Project names as free as possible (zeta3-progetti#17) and codes from the first four consonants
(zeta3-progetti#18), as decided by Rick on 21 October 2026."""

import pytest

from plane.api.serializers.project import ProjectCreateSerializer
from plane.app.serializers.project import ProjectSerializer
from plane.atlante.project_names import code_from_name, first_free, is_forbidden_name
from plane.atlante.tests.conftest import ADMIN, logged_in, make_project

CODE_URL = "/api/atlante/workspaces/spazio-prova/project-code/"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("Delta Vini - Social", "DLTV"),  # Rick's example
        ("Alfa Biscotti", "LFBS"),
        ("Città Studi", "CTTS"),  # accents dropped
        ("Gamma Palestre: sito", "GMMP"),
        ("Aia", "AIA"),  # fewer than four consonants: completed with the other letters
        ("Tè 2", "TE2"),
        ("--- !!!", "PROG"),  # nothing to use
    ],
)
def test_code_from_the_first_four_consonants(name, code):
    assert code_from_name(name) == code


@pytest.mark.unit
def test_a_taken_code_gets_a_number():
    assert first_free("DLTV", set()) == "DLTV"
    assert first_free("DLTV", {"DLTV"}) == "DLTV2"
    assert first_free("DLTV", {"dltv", "DLTV2"}) == "DLTV3"


@pytest.mark.unit
@pytest.mark.parametrize(
    "name",
    ["Delta Vini - Social", "Delta Vini: brand", "Pasticceria L'Arte & Co.", "Sito (2027)", "Social #estate 50%", "Chi? Noi!"],
)
def test_free_names_are_accepted(name):
    assert not is_forbidden_name(name)


@pytest.mark.unit
@pytest.mark.parametrize("name", ["<b>Delta</b>", "Delta > Vini", "=SOMMA(A1)", "+39 progetto", "-meno", "@cliente", "  =A1"])
def test_only_harmful_names_are_refused(name):
    assert is_forbidden_name(name)


@pytest.mark.contract
@pytest.mark.django_db
def test_the_interface_and_the_api_accept_the_dash(team):
    interface = ProjectSerializer(
        data={"name": "Delta Vini - Social", "identifier": "DLTV"}, context={"workspace_id": team.ws.id}
    )
    assert interface.is_valid(), interface.errors
    api = ProjectCreateSerializer(
        data={"name": "Delta Vini - Social", "identifier": "DLTV"}, context={"workspace_id": team.ws.id}
    )
    assert api.is_valid(), api.errors


@pytest.mark.contract
@pytest.mark.django_db
def test_harmful_names_and_codes_with_signs_are_still_refused(team):
    for data in ({"name": "<script>", "identifier": "SCRP"}, {"name": "=SOMMA(A1)", "identifier": "SMMA"}):
        assert not ProjectSerializer(data=data, context={"workspace_id": team.ws.id}).is_valid()
    # The code keeps Plane's rule: letters and digits only.
    assert not ProjectSerializer(
        data={"name": "Delta Vini - Social", "identifier": "DL-TV"}, context={"workspace_id": team.ws.id}
    ).is_valid()


@pytest.mark.contract
@pytest.mark.django_db
def test_the_proposed_code_skips_the_codes_already_used(team):
    admin = logged_in(team.admin)
    assert admin.get(CODE_URL, {"name": "Delta Vini - Social"}).data == {"code": "DLTV"}

    make_project(team.ws, "DLTV", [(team.admin, ADMIN)])
    assert admin.get(CODE_URL, {"name": "Delta Vini - Social"}).data == {"code": "DLTV2"}
    assert logged_in(team.membro).get(CODE_URL, {"name": "Delta Vini - Social"}).data == {"code": "DLTV2"}


@pytest.mark.contract
@pytest.mark.django_db
def test_only_the_team_asks_for_codes(team):
    assert logged_in(team.ospite).get(CODE_URL, {"name": "Delta"}).status_code == 403
    assert logged_in(team.estraneo).get(CODE_URL, {"name": "Delta"}).status_code == 403
    assert logged_in(team.admin).get(CODE_URL, {"name": " "}).status_code == 400
