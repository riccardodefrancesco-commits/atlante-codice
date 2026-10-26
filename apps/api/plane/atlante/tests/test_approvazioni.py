# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Assaggio F: Approva e Chiedi modifiche inside the task, the revision rounds of the client's contract,
15 calendar days with a reminder on the twelfth, an explicit yes for strategy, brand and site
(Condizioni Generali 3.0, articles 8.2 and 9.1; design system, table 15).

Until the portal (Rick, 22 October): the 15 days start when the team presses "Inviato al cliente",
the day of sending does not count, the silent consent is confirmed by a person."""

from datetime import date, timedelta

import pytest

from plane.atlante import approvals
from plane.atlante.models import Client, ClientApproval, PhaseBinding, ProjectClient, ProjectRole
from plane.atlante.phases import apply_template, enter_phase, today
from plane.atlante.tests.conftest import ADMIN, MEMBER, create, executors, logged_in, make_project, move
from plane.db.models import Issue, IssueActivity, Notification, ProjectMember

HOME = "/api/atlante/workspaces/spazio-prova/da-assegnare/"


def approval_url(video, issue):
    return f"{video.atlante}/issues/{issue.id}/approvazione/"


def answer(client, video, issue, **data):
    response = client.post(approval_url(video, issue), data, format="json")
    assert response.status_code == 200, response.content
    return Issue.objects.get(pk=issue.pk), response.data["approval"]


def to_client(client, video, issue, phase):
    """The task enters the phase and the work is sent: "Inviato al cliente"."""
    issue = move(client, video, issue, phase)
    issue, _ = answer(client, video, issue, esito="inviata")
    return issue


def sent_days_ago(issue, days):
    """As if the work had been sent `days` days ago."""
    sent = today() - timedelta(days=days)
    reminder, due = approvals.answer_days(sent)
    ClientApproval.objects.filter(issue=issue).update(sent_on=sent, reminder_on=reminder, due_on=due)


@pytest.mark.unit
def test_the_day_of_sending_does_not_count():
    # Rick's example: sent on 20 October, reminder on 1 November, answer until 4 November included.
    assert approvals.answer_days(date(2026, 10, 20)) == (date(2026, 11, 1), date(2026, 11, 4))


@pytest.mark.contract
@pytest.mark.django_db
def test_the_15_days_start_when_the_work_is_sent(team, video):
    member = logged_in(team.membro)
    issue, _ = create(member, video)
    issue = move(member, video, issue, "approvazione_script")
    data = member.get(approval_url(video, issue)).data["approval"]
    assert data["status"] == "da_inviare" and data["visible"]
    assert data["sent_on"] is None and data["due_on"] is None and data["days_left"] is None
    # Nothing to approve before it is sent.
    assert member.post(approval_url(video, issue), {"esito": "approvata"}, format="json").status_code == 400
    rows = logged_in(video.davide).get(HOME).data["approvals"]
    assert [(row["id"], row["ready"]) for row in rows] == [(str(issue.id), True)]

    issue, data = answer(member, video, issue, esito="inviata")
    assert data["status"] == "attesa" and data["sent_by"] == "Membro"
    assert data["sent_on"] == today().isoformat()
    assert data["reminder_on"] == (today() + timedelta(days=12)).isoformat()
    assert data["due_on"] == (today() + timedelta(days=15)).isoformat()
    assert (data["round"], data["included"], data["days_left"], data["to_confirm"]) == (1, 2, 15, False)
    assert IssueActivity.objects.filter(issue=issue, comment__startswith="Inviato al cliente da Membro").exists()
    assert member.post(approval_url(video, issue), {"esito": "inviata"}, format="json").status_code == 400
    # In the Home of the responsible person (Davide, the account), with the days left.
    rows = logged_in(video.davide).get(HOME).data["approvals"]
    assert [(row["id"], row["ready"], row["days_left"]) for row in rows] == [(str(issue.id), False, 15)]


@pytest.mark.contract
@pytest.mark.django_db
def test_approve_moves_the_task_on(team, video):
    member = logged_in(team.membro)
    issue, _ = create(member, video)
    issue = to_client(member, video, issue, "approvazione_script")
    issue, data = answer(member, video, issue, esito="approvata")
    assert issue.state_id == video.states["da_girare"].id
    assert executors(issue) == {video.daniele.id, video.virginia.id}  # the phase rule ran
    assert data["status"] == "approvata" and data["visible"] and data["next_state_name"] == "Da girare"
    line = IssueActivity.objects.filter(issue=issue, field="atlante_phase", comment__startswith="Approvata").get()
    assert "registrato da Membro" in line.comment


@pytest.mark.contract
@pytest.mark.django_db
def test_changes_go_back_with_the_same_urgency_and_count_the_rounds(team, video):
    member = logged_in(team.membro)
    issue, _ = create(member, video, priority="high")
    for _ in range(2):
        issue = to_client(member, video, issue, "approvazione_cliente")
        issue, data = answer(member, video, issue, esito="modifiche", nota="Il logo alla fine resta di più.")
        assert issue.state_id == video.states["montaggio"].id
        assert issue.priority == "high"
    assert approvals.used_rounds(issue) == 2
    last = IssueActivity.objects.filter(issue=issue, comment__startswith="Il cliente ha chiesto").latest("created_at")
    assert "«Il logo alla fine resta di più.»" in last.comment
    assert "giro extra, a pagamento" in last.comment  # the third round, with 2 included

    # A micro fix (file _1.1) does not count.
    issue = to_client(member, video, issue, "approvazione_cliente")
    assert member.get(approval_url(video, issue)).data["approval"]["round"] == 3
    issue, _ = answer(member, video, issue, esito="modifiche", nota="Una virgola.", conta=False)
    assert approvals.used_rounds(issue) == 2


@pytest.mark.contract
@pytest.mark.django_db
def test_the_rounds_included_are_those_of_the_clients_contract(team, video):
    client = Client.objects.create(workspace=team.ws, name="Delta Vini", code="DLTV", included_revisions=1)
    ProjectClient.objects.create(project=video.project, client=client, workspace=team.ws)
    member = logged_in(team.membro)
    issue, _ = create(member, video)
    issue = move(member, video, issue, "approvazione_cliente")
    data = member.get(approval_url(video, issue)).data["approval"]
    assert (data["round"], data["included"], data["client_name"]) == (1, 1, "Delta Vini")


@pytest.mark.contract
@pytest.mark.django_db
def test_reminder_on_day_12_and_silent_consent_to_confirm_from_day_16(team, video):
    member = logged_in(team.membro)
    issue, _ = create(member, video)
    issue = to_client(member, video, issue, "approvazione_cliente")
    nothing = {"reminders": 0, "to_confirm": 0, "late": 0}
    assert approvals.daily(today() + timedelta(days=11)) == nothing
    assert approvals.daily(today() + timedelta(days=12))["reminders"] == 1
    reminder = Notification.objects.get(
        entity_identifier=issue.id, data__issue_activity__field="atlante_client_reminder"
    )
    assert reminder.receiver_id == video.davide.id
    assert approvals.daily(today() + timedelta(days=13))["reminders"] == 0  # once

    # The fifteenth day is still the client's: nothing happens.
    assert approvals.daily(today() + timedelta(days=15)) == nothing
    # From the sixteenth day: silent consent to confirm. Atlante does not approve by itself.
    assert approvals.daily(today() + timedelta(days=16))["to_confirm"] == 1
    notice = Notification.objects.get(entity_identifier=issue.id, data__issue_activity__field="atlante_silent_consent")
    assert notice.receiver_id == video.davide.id
    assert approvals.daily(today() + timedelta(days=17))["to_confirm"] == 0  # told once
    issue = Issue.objects.get(pk=issue.pk)
    assert issue.state_id == video.states["approvazione_cliente"].id
    assert ClientApproval.objects.get(issue=issue).status == "attesa"


@pytest.mark.contract
@pytest.mark.django_db
def test_a_person_confirms_the_silent_consent(team, video):
    member = logged_in(team.membro)
    issue, _ = create(member, video)
    issue = to_client(member, video, issue, "approvazione_cliente")
    # Too early: on the fifteenth day the client can still answer.
    sent_days_ago(issue, 15)
    assert member.get(approval_url(video, issue)).data["approval"]["to_confirm"] is False
    assert member.post(approval_url(video, issue), {"esito": "silenzio_assenso"}, format="json").status_code == 400

    sent_days_ago(issue, 16)
    assert member.get(approval_url(video, issue)).data["approval"]["to_confirm"] is True
    issue, data = answer(member, video, issue, esito="silenzio_assenso")
    assert issue.state_id == video.states["pubblicazione"].id
    assert data["status"] == "approvata_auto" and data["decided_by"] == "Membro"
    line = IssueActivity.objects.filter(issue=issue, comment__startswith="Approvata per silenzio-assenso").get()
    assert "Confermata da Membro" in line.comment


@pytest.mark.contract
@pytest.mark.django_db
def test_brand_strategy_and_site_need_an_explicit_yes(team):
    project, _ = make_project(team.ws, "BRND", [(team.admin, ADMIN), (team.membro, MEMBER)])
    apply_template(project, "brand")
    ProjectRole.objects.create(project=project, role="account", member=team.admin)
    ok = PhaseBinding.objects.get(project=project, phase="ok_analisi").state
    issue = Issue.objects.create(project=project, workspace=team.ws, name="Analisi", state=ok)
    enter_phase(issue, created=True)
    approval = ClientApproval.objects.get(issue=issue)
    assert approval.consent is True
    approvals.send(issue, approval, team.admin)
    # The fifteenth day: only the reminder (the job did not run on the twelfth), the client still has time.
    assert approvals.daily(today() + timedelta(days=15)) == {"reminders": 1, "to_confirm": 0, "late": 0}
    assert approvals.daily(today() + timedelta(days=16)) == {"reminders": 0, "to_confirm": 0, "late": 1}
    assert Issue.objects.get(pk=issue.pk).state_id == ok.id  # it stays: no silent consent
    late = Notification.objects.get(entity_identifier=issue.id, data__issue_activity__field="atlante_client_late")
    assert late.receiver_id == team.admin.id
    assert approvals.daily(today() + timedelta(days=17))["late"] == 0  # told once
    # And nobody can confirm a silent consent for it.
    sent_days_ago(issue, 20)
    url = f"/api/atlante/workspaces/spazio-prova/projects/{project.id}/issues/{issue.id}/approvazione/"
    response = logged_in(team.membro).post(url, {"esito": "silenzio_assenso"}, format="json")
    assert response.status_code == 400 and "serve il sì" in response.data["error"]


@pytest.mark.contract
@pytest.mark.django_db
def test_moving_the_task_away_closes_the_wait(team, video):
    member = logged_in(team.membro)
    issue, _ = create(member, video)
    issue = to_client(member, video, issue, "approvazione_script")
    issue = move(member, video, issue, "da_girare")
    assert ClientApproval.objects.get(issue=issue).status == "superata"
    assert member.post(approval_url(video, issue), {"esito": "approvata"}, format="json").status_code == 400


@pytest.mark.contract
@pytest.mark.django_db
def test_the_cover_goes_back_to_its_graphics_and_is_done_when_approved(team, video):
    member = logged_in(team.membro)
    video_task, _ = create(member, video)
    cover = Issue.issue_objects.get(parent=video_task)
    cover = to_client(member, video, cover, "approvazione_cliente")
    cover, _ = answer(member, video, cover, esito="modifiche", nota="Più contrasto.")
    assert cover.state_id == video.states["grafica_copertina"].id
    cover = to_client(member, video, cover, "approvazione_cliente")
    cover, _ = answer(member, video, cover, esito="approvata")
    assert cover.state_id == video.states["fatto"].id


@pytest.mark.contract
@pytest.mark.django_db
def test_only_the_team_answers_for_the_client(team, video):
    member = logged_in(team.membro)
    issue, _ = create(member, video)
    issue = to_client(member, video, issue, "approvazione_script")
    ProjectMember.objects.create(project=video.project, member=team.estraneo, role=5, workspace=team.ws)
    for person in (team.ospite, team.estraneo):
        client = logged_in(person)
        assert client.get(approval_url(video, issue)).status_code == 403
        assert client.post(approval_url(video, issue), {"esito": "approvata"}, format="json").status_code == 403
    assert member.post(approval_url(video, issue), {"esito": "forse"}, format="json").status_code == 400
    assert Issue.objects.get(pk=issue.pk).state_id == video.states["approvazione_script"].id
