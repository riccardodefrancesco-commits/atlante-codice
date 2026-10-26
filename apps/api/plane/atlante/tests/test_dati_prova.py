# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The invented test data: created only in the test environment, never twice."""

import secrets

import pytest
from django.core.management import call_command
from django.utils import timezone
from django.core.management.base import CommandError

from plane.atlante.models import Client, IssueClient, PhaseEntry, ProjectClient, ProjectTemplate
from plane.db.models import Issue, IssueAssignee, Project, ProjectMember, User, Workspace, WorkspaceMember
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration

PASSWORD = "password-di-prova-per-i-test"


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
def test_environment(monkeypatch):
    monkeypatch.setenv("ATLANTE_AMBIENTE", "prova")
    monkeypatch.setenv("ATLANTE_PASSWORD_PROVA", PASSWORD)


@pytest.mark.unit
@pytest.mark.django_db
def test_refuses_outside_test_environment(instance, monkeypatch):
    monkeypatch.delenv("ATLANTE_AMBIENTE", raising=False)
    monkeypatch.setenv("ATLANTE_PASSWORD_PROVA", PASSWORD)
    with pytest.raises(CommandError):
        call_command("atlante_dati_prova")
    assert not Workspace.objects.exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_creates_invented_workspace(instance, test_environment):
    call_command("atlante_dati_prova")

    workspace = Workspace.objects.get(slug="zeta3-prova")
    assert WorkspaceMember.objects.filter(workspace=workspace).count() == 7
    # Only invented people; the other user is the "Atlante" automation, which cannot sign in.
    assert all(u.email.endswith("@esempio.it") for u in User.objects.filter(is_bot=False))
    assert list(User.objects.filter(is_bot=True).values_list("is_active", flat=True)) == [False]
    assert User.objects.get(email="admin@esempio.it").check_password(PASSWORD)
    assert User.objects.get(email="anna@esempio.it").user_timezone == "Europe/Rome"
    assert InstanceAdmin.objects.filter(user__email="admin@esempio.it").exists()
    instance.refresh_from_db()
    assert instance.is_setup_done is True
    assert InstanceConfiguration.objects.get(key="ENABLE_SIGNUP").value == "0"

    projects = Project.objects.filter(workspace=workspace)
    assert projects.count() == 7
    assert not projects.filter(cycle_view=True).exists()  # cycles hidden
    assert Issue.issue_objects.filter(workspace=workspace).count() == 6 * 33 + 12  # 6 videos with their covers

    # The Video project (assaggio B): template, roles, and tasks already moved by the phase rules.
    assert ProjectTemplate.objects.get(project__identifier="ALFV").template == "video"
    reel = Issue.issue_objects.get(project__identifier="ALFV", name="Reel evento di novembre")
    assert reel.state.name == "Revisione interna"
    executors = IssueAssignee.objects.filter(issue=reel).values_list("assignee__email", flat=True)
    assert set(executors) == {"admin@esempio.it", "bruno@esempio.it"}
    assert PhaseEntry.objects.filter(issue=reel).count() == 6

    guest_projects = ProjectMember.objects.filter(member__email="fabio@esempio.it").values_list(
        "project__identifier", flat=True
    )
    assert sorted(guest_projects) == ["ALFA", "ALFV"]

    # Invented clients: one per client project, none on VIDEO and INT, own clients on VIDEO items.
    assert Client.objects.filter(workspace=workspace).count() == 4
    assert ProjectClient.objects.get(project__identifier="ALFA").client.code == "ALF"
    assert not ProjectClient.objects.filter(project__identifier__in=["VIDEO", "INT"]).exists()
    video_items = Issue.issue_objects.filter(project__identifier="VIDEO").count()
    assert IssueClient.objects.filter(project__identifier="VIDEO").count() == video_items

    # Every work item has a readable creator, not an empty one.
    assert not Issue.issue_objects.filter(workspace=workspace, created_by__isnull=True).exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_adds_clients_to_data_created_before_clients(instance, test_environment):
    call_command("atlante_dati_prova")
    Client.all_objects.all().delete()  # as if the data came from piece 1
    IssueClient.objects.all().delete()
    ProjectClient.objects.all().delete()
    call_command("atlante_dati_prova")
    assert Client.objects.count() == 4


@pytest.mark.unit
@pytest.mark.django_db
def test_does_not_run_twice(instance, test_environment):
    call_command("atlante_dati_prova")
    with pytest.raises(CommandError):
        call_command("atlante_dati_prova")


@pytest.mark.unit
@pytest.mark.django_db
def test_extra_items_for_speed_test(instance, test_environment):
    call_command("atlante_dati_prova")
    call_command("atlante_dati_prova", lavori_extra=60)
    assert Issue.issue_objects.filter(workspace__slug="zeta3-prova").count() == 6 * 33 + 12 + 60
