# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The data of the online trial (zeta3-progetti, docs/collaudo-0.3.md, section 2): created from scratch
in their own workspace, every task in its phase by the phase rules, never touching another workspace."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from plane.atlante import approvals
from plane.atlante.models import ClientApproval, Client, ProjectClient, ProjectRole, TaskDate
from plane.atlante.monthly_reports import REPORT_DAYS
from plane.atlante.phases import ROME, is_to_assign, today
from plane.atlante.tests.conftest import ADMIN, MEMBER, PEOPLE_FILE, make_project, make_user
from plane.atlante.working_days import add_working_days
from plane.db.models import (
    Issue,
    IssueActivity,
    IssueAssignee,
    Notification,
    ProjectMember,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.license.models import InstanceAdmin, InstanceConfiguration


def task(name):
    return Issue.issue_objects.get(workspace__slug="zeta3-collaudo", name=name)


def doers(issue):
    return set(IssueAssignee.objects.filter(issue=issue).values_list("assignee__first_name", flat=True))


def box(issue):
    return ClientApproval.objects.exclude(status=ClientApproval.PASSED).filter(issue=issue).latest("created_at")


def day_of(moment):
    return timezone.localtime(moment, ROME).date()


@pytest.mark.unit
@pytest.mark.django_db
def test_refuses_outside_test_environment(instance, people_file, monkeypatch):
    monkeypatch.delenv("ATLANTE_AMBIENTE")
    with pytest.raises(CommandError):
        call_command("atlante_dati_collaudo", persone=people_file)
    assert not Workspace.objects.exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_people_and_projects(instance, people_file):
    call_command("atlante_dati_collaudo", persone=people_file)

    workspace = Workspace.objects.get(slug="zeta3-collaudo")
    assert workspace.name == "Zeta3 Collaudo"
    roles = dict(WorkspaceMember.objects.filter(workspace=workspace).values_list("member__display_name", "role"))
    assert roles == {
        "rick": ADMIN,
        "alessandra": ADMIN,
        "virginia": MEMBER,
        "giulia": MEMBER,
        "dario": MEMBER,
        "carla": MEMBER,
    }
    assert User.objects.get(email="alessandra@lavoro.esempio.it").check_password("password-alessandra-prova")
    # The invented colleagues never sign in.
    assert not User.objects.get(email="dario@collaudo.esempio.it").has_usable_password()
    # A new installation: Rick administers it; nobody signs up alone.
    assert InstanceAdmin.objects.get().user.email == "rick@lavoro.esempio.it"
    assert InstanceConfiguration.objects.get(key="ENABLE_SIGNUP").value == "0"

    for identifier in ("ALFV", "ALFS"):
        members = dict(
            ProjectMember.objects.filter(project__identifier=identifier).values_list("member__display_name", "role")
        )
        assert members == {
            **{who: MEMBER for who in ("virginia", "giulia", "dario", "carla")},
            "rick": ADMIN,
            "alessandra": ADMIN,
        }
        assert ProjectClient.objects.get(project__identifier=identifier).client.name == "Alfa Biscotti"
    video_roles = ProjectRole.objects.filter(project__identifier="ALFV")
    assert not video_roles.filter(role="videomaker").exists()
    assert video_roles.get(role="editor").member.display_name == "virginia"
    zeta = Client.objects.get(workspace=workspace, name="Zeta Gelati")
    assert not ProjectClient.objects.filter(client=zeta).exists()
    assert Client.objects.get(workspace=workspace, name="Alfa Biscotti").included_revisions == 2


@pytest.mark.unit
@pytest.mark.django_db
def test_every_task_is_in_its_phase(instance, people_file):
    call_command("atlante_dati_collaudo", persone=people_file)
    day = today()

    offer = task("Reel offerta del mese")
    assert offer.state.name == "Approvazione script"
    assert box(offer).status == ClientApproval.READY
    assert doers(offer) == {"Alessandra"}

    interview = task("Video intervista al fondatore")
    assert interview.state.name == "Approvazione cliente"
    assert box(interview).sent_on == day - timedelta(days=16)
    assert approvals.silent_consent_due(box(interview))

    behind = task("Reel dietro le quinte")
    assert behind.state.name == "Approvazione cliente"
    assert (box(behind).due_on - day).days == 12
    assert (box(behind).round, approvals.included_rounds(behind)) == (1, 2)

    christmas = task("Reel ricetta di Natale")
    assert christmas.state.name == "Da girare"
    assert is_to_assign(christmas)
    assert christmas.target_date == day + timedelta(days=7)  # the day of the shooting

    tutorial = task("Reel tutorial ricetta")
    assert (tutorial.state.name, tutorial.priority, doers(tutorial)) == ("In montaggio", "urgent", {"Virginia"})
    assert tutorial.target_date == add_working_days(day, 1)

    chef = task("Montaggio intervista chef")
    assert (chef.state.name, doers(chef)) == ("In montaggio", {"Virginia"})
    assert chef.target_date == add_working_days(day, -1)  # late

    autumn = task("Carosello ricette d'autunno")
    publication = TaskDate.objects.get(issue=autumn, kind="pubblicazione").day
    assert (autumn.state.name, doers(autumn)) == ("Struttura del post", {"Giulia"})
    assert publication == day + timedelta(days=21)
    assert autumn.target_date == add_working_days(publication, -10)
    assert task("Post lancio biscotto al cacao").state.name == "Struttura del post"

    christmas_post = task("Post offerta di Natale")
    assert (christmas_post.state.name, doers(christmas_post)) == ("Revisione interna", {"Giulia"})

    scheduled = task("Carosello dietro le quinte")
    assert (scheduled.state.name, doers(scheduled)) == ("Schedulato o pubblicato", {"Giulia"})
    assert scheduled.target_date == day + timedelta(days=5)

    first = day.replace(day=1)
    report = Issue.issue_objects.get(workspace__slug="zeta3-collaudo", name__startswith="Report mensile:")
    assert (report.state.name, doers(report)) == ("Da pianificare", {"Giulia"})
    assert report.target_date == add_working_days(first, REPORT_DAYS)
    assert day_of(report.created_at) == first

    # Every video has its cover, for Carla.
    covers = Issue.issue_objects.filter(project__identifier="ALFV", parent__isnull=False)
    assert covers.count() == 6
    assert {name for cover in covers for name in doers(cover)} == {"Carla"}


@pytest.mark.unit
@pytest.mark.django_db
def test_the_history_has_the_days_of_the_plan(instance, people_file):
    call_command("atlante_dati_collaudo", persone=people_file)
    day = today()
    interview = task("Video intervista al fondatore")

    sent = IssueActivity.objects.filter(issue=interview, comment__startswith="Inviato al cliente").order_by(
        "created_at"
    )
    assert [day_of(line.created_at) for line in sent] == [day - timedelta(days=28), day - timedelta(days=16)]
    assert "Alessandra" in sent.last().comment
    assert day_of(interview.created_at) == day - timedelta(days=30)
    # The person who moved it, as from the board, and the morning job: reminder on day 12, then to confirm.
    moved = IssueActivity.objects.get(issue=interview, field="state", new_value="Approvazione cliente")
    assert (moved.actor.display_name, day_of(moved.created_at)) == ("giulia", day - timedelta(days=16))
    reminder = IssueActivity.objects.get(issue=interview, comment__startswith="Giorno del promemoria")
    assert day_of(reminder.created_at) == day - timedelta(days=4)
    assert IssueActivity.objects.filter(issue=interview, comment__contains="silenzio-assenso da confermare").exists()
    # The notices of the preparation are already read.
    assert not Notification.objects.filter(workspace__slug="zeta3-collaudo", read_at__isnull=True).exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_never_touches_another_workspace(instance, people_file):
    owner = make_user("altro")
    other = Workspace.objects.create(name="Zeta3 Prova", slug="zeta3-prova", owner=owner)
    WorkspaceMember.objects.create(workspace=other, member=owner, role=ADMIN)
    project, states = make_project(other, "ALTR", [(owner, ADMIN)])
    old = Issue.objects.create(project=project, workspace=other, name="Lavoro di Rick", state=states["started"])
    waiting = ClientApproval.objects.create(
        issue=old,
        state=states["started"],
        phase="approvazione_cliente",
        status=ClientApproval.WAITING,
        sent_on=today() - timedelta(days=20),
        reminder_on=today() - timedelta(days=8),
        due_on=today() - timedelta(days=5),
    )
    before = IssueActivity.objects.filter(workspace=other).count()

    call_command("atlante_dati_collaudo", persone=people_file)

    waiting.refresh_from_db()
    assert (waiting.reminded_at, waiting.late_notice_at) == (None, None)
    assert IssueActivity.objects.filter(workspace=other).count() == before
    assert not Notification.objects.filter(workspace=other).exists()
    assert Issue.issue_objects.filter(workspace=other).count() == 1


@pytest.mark.unit
@pytest.mark.django_db
def test_never_twice_and_a_second_round_archives_the_first(instance, people_file):
    call_command("atlante_dati_collaudo", persone=people_file)
    giulia = User.objects.get(email="giulia@lavoro.esempio.it")
    giulia.set_password("la-password-scelta-da-giulia")  # changed at the first sign in
    giulia.save()
    with pytest.raises(CommandError):
        call_command("atlante_dati_collaudo", persone=people_file)

    call_command("atlante_dati_collaudo", persone=people_file, nuovo_giro=True)

    first = Workspace.objects.get(slug="zeta3-collaudo-giro-1")
    assert not WorkspaceMember.objects.filter(workspace=first, is_active=True).exists()
    assert (
        Issue.issue_objects.filter(workspace=first).count()
        == Issue.issue_objects.filter(workspace__slug="zeta3-collaudo").count()
    )
    # Who has an account keeps it, with the password they chose.
    assert User.objects.filter(email="giulia@lavoro.esempio.it").count() == 1
    assert User.objects.get(email="giulia@lavoro.esempio.it").check_password("la-password-scelta-da-giulia")


@pytest.mark.unit
@pytest.mark.django_db
def test_the_file_needs_the_four_people(instance, people_file, tmp_path):
    short = tmp_path / "corto.md"
    short.write_text(PEOPLE_FILE.replace("| giulia |", "| marta |"), encoding="utf-8")
    with pytest.raises(CommandError):
        call_command("atlante_dati_collaudo", persone=str(short))
    assert not Workspace.objects.filter(slug="zeta3-collaudo").exists()
