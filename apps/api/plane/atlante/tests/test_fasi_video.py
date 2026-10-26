# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Assaggio B, the Video template (docs/specifica/08-fasi-dei-contenuti.md, section 4): the phases
change executor and deadline by themselves, from the roles of the project and the choices on the task.
Rick's condition (22 October): renaming, recoloring and reordering the phases never breaks the rules."""

from datetime import date, timedelta

import pytest

from plane.atlante.models import PhaseBinding, PhaseEntry, ProjectRole, ProjectTemplate, TaskAssignment, TaskType
from plane.atlante.phases import AUTOMATION_EMAIL, apply_template, today
from plane.atlante.project_templates import TEMPLATES, VIDEO
from plane.atlante.tests.conftest import ADMIN, MEMBER, create, executors, logged_in, make_issue, make_project, move
from plane.atlante.working_days import add_working_days, easter, holidays, is_working_day
from plane.db.models import Issue, IssueActivity, Notification, State, User


# Working days (section 9)


@pytest.mark.unit
def test_easter_and_the_holidays_are_skipped():
    assert easter(2026) == date(2026, 4, 5)
    assert easter(2027) == date(2027, 3, 28)
    assert not is_working_day(date(2027, 3, 29))  # Easter Monday
    assert not is_working_day(date(2026, 6, 24))  # San Giovanni, Turin
    assert add_working_days(date(2026, 10, 23), 1) == date(2026, 10, 26)  # Friday to Monday
    assert add_working_days(date(2026, 12, 24), 1) == date(2026, 12, 28)  # Christmas, Santo Stefano, Sunday
    assert add_working_days(date(2026, 6, 23), 1) == date(2026, 6, 25)
    assert add_working_days(date(2027, 3, 31), -2) == date(2027, 3, 26)  # back over Easter Monday
    # San Francesco, national holiday from 2026 (law 151 of 8 October 2025): not before.
    assert not is_working_day(date(2027, 10, 4))
    assert add_working_days(date(2027, 10, 1), 1) == date(2027, 10, 5)
    assert date(2025, 10, 4) not in holidays(2025) and date(2026, 10, 4) in holidays(2026)


# The template on a project


@pytest.mark.contract
@pytest.mark.django_db
def test_the_template_reuses_planes_states_and_deletes_nothing(team):
    project, plane_states = make_project(team.ws, "VIDE", [(team.admin, ADMIN)])
    before = set(State.all_state_objects.filter(project=project).values_list("id", flat=True))
    apply_template(project, "video")

    states = State.objects.filter(project=project, atlante_phase__isnull=False).order_by("sequence")
    assert [s.name for s in states] == [phase.name for phase in VIDEO.phases]
    assert before <= set(State.all_state_objects.filter(project=project).values_list("id", flat=True))
    assert State.all_state_objects.filter(project=project, deleted_at__isnull=False).count() == 0
    # Plane's five states became phases: "Da fare" is now "Script", the default for new tasks.
    assert State.objects.get(pk=plane_states["unstarted"].pk).name == "Script"
    assert State.objects.get(project=project, default=True).name == "Script"
    assert ProjectTemplate.objects.get(project=project).template == "video"

    # Applying it again changes nothing, even after the admins renamed a phase.
    State.objects.filter(pk=plane_states["started"].pk).update(name="Ok dello script")
    apply_template(project, "video")
    assert State.objects.filter(project=project).count() == len(VIDEO.phases)
    assert State.objects.get(pk=plane_states["started"].pk).name == "Ok dello script"


@pytest.mark.contract
@pytest.mark.django_db
def test_a_project_with_tasks_keeps_its_states(team):
    project, plane_states = make_project(team.ws, "VECC", [(team.admin, ADMIN)])
    old = make_issue(project, plane_states["started"])
    apply_template(project, "video")
    # The state with a task keeps its name and has no phase: its task does not change meaning.
    state = State.objects.get(pk=plane_states["started"].pk)
    assert state.name == "In corso" and not PhaseBinding.objects.filter(state=state).exists()
    assert Issue.objects.get(pk=old.pk).state_id == state.id


# The phases change executor and deadline


@pytest.mark.contract
@pytest.mark.django_db
def test_a_new_task_starts_in_script_with_the_social_media_manager(team, video):
    issue, data = create(logged_in(team.membro), video, priority="medium")
    assert issue.state_id == video.states["script"].id
    assert executors(issue) == {video.giulia.id}
    # No shooting date yet: the urgency counts (Media, 7 working days).
    assert issue.target_date == add_working_days(today(), 7)
    # The answer already shows them, so the screen is right at once.
    assert [str(member_id) for member_id in data["assignee_ids"]] == [str(video.giulia.id)]
    assert str(data["target_date"]) == issue.target_date.isoformat()
    # The first line is the phase rule; the second says that the cover was created.
    line = IssueActivity.objects.filter(issue=issue, field="atlante_phase").order_by("created_at").first()
    assert line.actor.email == AUTOMATION_EMAIL and line.actor.is_bot and not line.actor.is_active
    assert "Giulia" in line.comment and "7 giorni lavorativi" in line.comment


@pytest.mark.contract
@pytest.mark.django_db
def test_the_choices_made_in_the_form_stay(team, video):
    chosen_day = today() + timedelta(days=40)
    issue, _ = create(
        logged_in(team.membro), video, assignee_ids=[str(video.edoardo.id)], target_date=chosen_day.isoformat()
    )
    assert executors(issue) == {video.edoardo.id}
    assert issue.target_date == chosen_day


@pytest.mark.contract
@pytest.mark.django_db
def test_the_video_goes_through_its_phases(team, video):
    member = logged_in(team.membro)
    issue, _ = create(member, video, priority="high")

    # The shooting date moves the script deadline: 2 working days before, skipping Easter Monday.
    response = member.patch(f"{video.atlante}/issues/{issue.id}/scelte/", {"riprese": "2027-03-31"}, format="json")
    assert response.status_code == 200, response.content
    assert Issue.objects.get(pk=issue.pk).target_date == date(2027, 3, 26)

    issue = move(member, video, issue, "approvazione_script")
    assert executors(issue) == {video.davide.id}  # the account, responsible of the task
    assert issue.target_date == today() + timedelta(days=15)  # calendar days, as in the contract

    issue = move(member, video, issue, "da_girare")
    assert executors(issue) == {video.daniele.id, video.virginia.id}
    assert issue.target_date == date(2027, 3, 31)

    issue = move(member, video, issue, "girato")
    assert executors(issue) == {video.daniele.id}
    assert issue.target_date == add_working_days(today(), 3)  # Alta: 3 working days

    # In "Girato" the lead videomaker picks the editor of this video.
    member.patch(f"{video.atlante}/issues/{issue.id}/scelte/", {"editor": [str(video.edoardo.id)]}, format="json")
    issue = move(member, video, issue, "montaggio")
    assert executors(issue) == {video.edoardo.id}
    assert issue.target_date == add_working_days(today(), 3)

    issue = move(member, video, issue, "revisione_interna")
    assert executors(issue) == {video.giulia.id, video.rick.id}
    assert issue.target_date == add_working_days(today(), 2)

    # Changes asked: back to "In montaggio" with the same urgency.
    issue = move(member, video, issue, "montaggio")
    assert executors(issue) == {video.edoardo.id}
    assert issue.target_date == add_working_days(today(), 3)

    entries = PhaseEntry.objects.filter(issue=issue).order_by("created_at")
    assert [e.phase for e in entries] == [
        "script",
        "approvazione_script",
        "da_girare",
        "girato",
        "montaggio",
        "revisione_interna",
        "montaggio",
    ]


@pytest.mark.contract
@pytest.mark.django_db
def test_renaming_recoloring_and_reordering_never_break_the_rules(team, video):
    """Rick's condition for assaggio B."""
    admin = logged_in(team.admin)
    state = video.states["approvazione_cliente"]
    response = admin.patch(
        f"{video.base}/states/{state.id}/",
        {"name": "Al cliente per l'ok", "color": "#111111", "sequence": 1000},
        format="json",
    )
    assert response.status_code == 200, response.content
    assert State.objects.get(pk=state.pk).name == "Al cliente per l'ok"

    # Plane's "Approvazione script" renamed to the old name of the other phase: the rules follow the role.
    admin.patch(f"{video.base}/states/{video.states['script'].id}/", {"name": "Approvazione cliente"}, format="json")

    issue, _ = create(logged_in(team.membro), video)
    issue = move(logged_in(team.membro), video, issue, "approvazione_cliente")
    assert executors(issue) == {video.davide.id}
    assert issue.target_date == today() + timedelta(days=15)
    assert PhaseEntry.objects.filter(issue=issue).latest("created_at").phase == "approvazione_cliente"


@pytest.mark.contract
@pytest.mark.django_db
def test_a_state_added_by_the_admins_has_no_rule(team, video):
    admin = logged_in(team.admin)
    response = admin.post(
        f"{video.base}/states/", {"name": "Musica da scegliere", "color": "#222222", "group": "started"}, format="json"
    )
    assert response.status_code in (200, 201), response.content
    issue, _ = create(logged_in(team.membro), video)
    before = (executors(issue), Issue.objects.get(pk=issue.pk).target_date)
    issue.state_id = response.data["id"]
    issue.save()
    assert (executors(issue), Issue.objects.get(pk=issue.pk).target_date) == before


@pytest.mark.contract
@pytest.mark.django_db
def test_an_empty_role_leaves_the_task_to_assign(team, video):
    """Rick, 22 October: nobody in the role, the task stays without executor ("Da assegnare"), the people
    of the phase before do not keep it, and the urgency days start when someone is assigned."""
    member = logged_in(team.membro)
    ProjectRole.objects.filter(project=video.project, role="lead_videomaker").delete()
    issue, _ = create(member, video, priority="high")
    issue = move(member, video, issue, "da_girare")
    assert executors(issue) == {video.daniele.id, video.virginia.id}

    issue = move(member, video, issue, "girato")
    assert executors(issue) == set()
    assert issue.target_date is None  # the urgency waits for the assignment
    line = IssueActivity.objects.filter(issue=issue, field="atlante_phase").latest("created_at").comment
    assert "Nessuno nel ruolo Lead videomaker: la task è da assegnare e chi ci lavorava prima non la tiene" in line
    choices = member.get(f"{video.atlante}/issues/{issue.id}/scelte/").data
    assert choices["to_assign"] is True

    # It is in the Home of the responsible person (Davide, the account), not in other people's.
    home = logged_in(video.davide).get("/api/atlante/workspaces/spazio-prova/da-assegnare/").data
    assert [row["id"] for row in home["to_assign"]] == [str(issue.id)]
    assert home["without_responsible"] is None  # only for workspace admins
    assert logged_in(video.giulia).get("/api/atlante/workspaces/spazio-prova/da-assegnare/").data["to_assign"] == []

    # Someone assigned by hand: the 3 working days of "Prioritario" start today.
    response = member.patch(
        f"{video.base}/issues/{issue.id}/", {"assignee_ids": [str(video.edoardo.id)]}, format="json"
    )
    assert response.status_code == 204, response.content
    issue = Issue.objects.get(pk=issue.pk)
    assert issue.target_date == add_working_days(today(), 3)
    assert TaskAssignment.objects.get(issue=issue).assigned_on == today()
    assert member.get(f"{video.atlante}/issues/{issue.id}/scelte/").data["to_assign"] is False
    assert logged_in(video.davide).get("/api/atlante/workspaces/spazio-prova/da-assegnare/").data["to_assign"] == []


@pytest.mark.contract
@pytest.mark.django_db
def test_without_reviewers_the_responsible_person_reviews(team, video):
    """Design system, table 14: reviewers are not required; without them the responsible person reviews."""
    ProjectRole.objects.filter(project=video.project, role="revisore_interno").delete()
    member = logged_in(team.membro)
    issue, _ = create(member, video)
    issue = move(member, video, issue, "revisione_interna")
    assert executors(issue) == {video.davide.id}
    assert issue.target_date == add_working_days(today(), 2)


@pytest.mark.contract
@pytest.mark.django_db
def test_without_responsible_person_the_client_phases_are_to_assign(team, video):
    ProjectRole.objects.filter(project=video.project, role="account").delete()
    member = logged_in(team.membro)
    issue, _ = create(member, video)
    issue = move(member, video, issue, "approvazione_cliente")
    assert executors(issue) == set()
    assert "Manca il responsabile: la task è da assegnare" in (
        IssueActivity.objects.filter(issue=issue, field="atlante_phase").latest("created_at").comment
    )
    # The client's 15 calendar days do not wait for anyone.
    assert issue.target_date == today() + timedelta(days=15)
    # Workspace admins see it among the tasks without a responsible person.
    home = logged_in(team.admin).get("/api/atlante/workspaces/spazio-prova/da-assegnare/").data
    assert str(issue.id) in [row["id"] for row in home["without_responsible"]]


@pytest.mark.contract
@pytest.mark.django_db
def test_the_urgency_counts_from_the_assignment_in_every_project(team):
    """Rick, 22 October: the urgency with the days holds for every kind of work, not only video."""
    project, _ = make_project(team.ws, "INTE", [(team.admin, ADMIN), (team.membro, MEMBER)])
    base = f"/api/workspaces/spazio-prova/projects/{project.id}"
    member = logged_in(team.membro)
    response = member.post(
        f"{base}/issues/",
        {"name": "Preventivo", "priority": "high", "assignee_ids": [str(team.membro.id)]},
        format="json",
    )
    issue = Issue.objects.get(pk=response.data["id"])
    assert issue.target_date == add_working_days(today(), 3)  # Prioritario

    member.patch(f"{base}/issues/{issue.id}/", {"priority": "urgent"}, format="json")
    assert Issue.objects.get(pk=issue.pk).target_date == add_working_days(today(), 1)  # Urgente, from the same day
    line = IssueActivity.objects.filter(issue=issue, field="atlante_phase").latest("created_at").comment
    assert "Urgente: 1 giorno lavorativo dall'assegnazione" in line

    # A task without executor has no delivery date until someone gets it.
    response = member.post(f"{base}/issues/", {"name": "Listino", "priority": "low"}, format="json")
    later = Issue.objects.get(pk=response.data["id"])
    assert later.target_date is None
    member.patch(f"{base}/issues/{later.id}/", {"assignee_ids": [str(team.admin.id)]}, format="json")
    assert Issue.objects.get(pk=later.pk).target_date == add_working_days(today(), 10)  # In blocco

    # Without urgency there is no automatic delivery date: it is set by hand.
    response = member.post(
        f"{base}/issues/", {"name": "Bozza", "priority": "none", "assignee_ids": [str(team.membro.id)]}, format="json"
    )
    assert Issue.objects.get(pk=response.data["id"]).target_date is None

    # A delivery date chosen by hand stays, until the urgency or the executor changes.
    member.patch(f"{base}/issues/{later.id}/", {"target_date": "2027-01-29"}, format="json")
    member.patch(f"{base}/issues/{later.id}/", {"name": "Listino 2027"}, format="json")
    assert Issue.objects.get(pk=later.pk).target_date == date(2027, 1, 29)


@pytest.mark.contract
@pytest.mark.django_db
def test_the_responsible_person_chosen_on_the_task_gets_the_client_phases(team, video):
    member = logged_in(team.membro)
    issue, _ = create(member, video)
    response = member.patch(
        f"{video.atlante}/issues/{issue.id}/scelte/", {"responsabile": str(video.rick.id)}, format="json"
    )
    assert response.data["responsabile"] == {"member_id": str(video.rick.id), "source": "task"}
    issue = move(member, video, issue, "approvazione_cliente")
    assert executors(issue) == {video.rick.id}


# Permissions


@pytest.mark.contract
@pytest.mark.django_db
def test_only_project_admins_change_template_and_roles(team, video):
    member, admin = logged_in(team.membro), logged_in(team.admin)
    assert member.post(f"{video.atlante}/modello/", {"template": "video"}, format="json").status_code == 403
    body = {"role": "editor", "member_ids": [str(video.virginia.id)]}
    assert member.put(f"{video.atlante}/ruoli/", body, format="json").status_code == 403
    assert member.get(f"{video.atlante}/modello/").status_code == 200

    response = admin.put(
        f"{video.atlante}/ruoli/", {"role": "editor", "member_ids": [str(video.edoardo.id)]}, format="json"
    )
    assert response.status_code == 200
    editor = next(role for role in response.data["roles"] if role["key"] == "editor")
    assert editor["member_ids"] == [str(video.edoardo.id)]
    assert admin.post(f"{video.atlante}/modello/", {"template": "podcast"}, format="json").status_code == 400


@pytest.mark.contract
@pytest.mark.django_db
def test_guests_and_strangers_see_nothing(team, video):
    issue = make_issue(video.project, video.states["script"])
    for person in (team.ospite, team.estraneo):
        client = logged_in(person)
        assert client.get(f"{video.atlante}/modello/").status_code == 403
        assert client.get(f"{video.atlante}/issues/{issue.id}/scelte/").status_code == 403
        assert (
            client.patch(f"{video.atlante}/issues/{issue.id}/scelte/", {"riprese": None}, format="json").status_code
            == 403
        )


@pytest.mark.contract
@pytest.mark.django_db
def test_wrong_choices_are_refused_and_nothing_is_written(team, video):
    member, admin = logged_in(team.membro), logged_in(team.admin)
    issue = make_issue(video.project, video.states["script"])
    url = f"{video.atlante}/issues/{issue.id}/scelte/"
    # A guest cannot work on the task, an unknown field is refused, a wrong date too.
    assert member.patch(url, {"editor": [str(team.ospite.id)]}, format="json").status_code == 400
    assert member.patch(url, {"responsabile": "non-un-id"}, format="json").status_code == 400
    assert member.patch(url, {"budget": 10}, format="json").status_code == 400
    response = member.patch(url, {"editor": [str(video.edoardo.id)], "riprese": "31/03/2027"}, format="json")
    assert response.status_code == 400
    assert member.get(url).data["roles"][1]["member_ids"] == []  # the editor was not saved either
    body = {"role": "editor", "member_ids": [str(team.ospite.id)]}
    assert admin.put(f"{video.atlante}/ruoli/", body, format="json").status_code == 400


@pytest.mark.contract
@pytest.mark.django_db
def test_the_automation_cannot_sign_in(team, video):
    create(logged_in(team.membro), video)
    bot = User.objects.get(email=AUTOMATION_EMAIL)
    assert not bot.is_active and not bot.has_usable_password() and bot.is_bot


# The other templates, the kind of work and the cover (release 0.3)


@pytest.mark.contract
@pytest.mark.django_db
@pytest.mark.parametrize("key", sorted(TEMPLATES))
def test_every_template_applies_to_a_new_project(team, key):
    project, _ = make_project(team.ws, key[:4].upper() + "X", [(team.admin, ADMIN)])
    apply_template(project, key)
    template = TEMPLATES[key]
    names = list(
        State.objects.filter(project=project, atlante_phase__isnull=False)
        .order_by("sequence")
        .values_list("name", flat=True)
    )
    assert names == [phase.name for phase in template.phases]
    default = next(phase for phase in template.phases if phase.default)
    assert State.objects.get(project=project, default=True).name == default.name


@pytest.mark.contract
@pytest.mark.django_db
def test_a_new_video_gets_its_cover(team, video):
    """Request 36: with the video, its cover, for the graphic designer, as a sub-task of the video."""
    issue, _ = create(logged_in(team.membro), video)
    cover = Issue.issue_objects.get(parent=issue)
    assert cover.name == "Copertina: Reel di ottobre"
    assert cover.state_id == video.states["grafica_copertina"].id
    assert executors(cover) == {video.edoardo.id}
    assert TaskType.objects.get(issue=issue).kind == "video"
    assert TaskType.objects.get(issue=cover).kind == "copertina"
    assert "Daniele" in cover.description_html and "Virginia" in cover.description_html
    assert (
        "Creata la task della copertina"
        in IssueActivity.objects.filter(issue=issue, field="atlante_phase").latest("created_at").comment
    )
    # The cover is due with the video: when the edit has its delivery date, the cover follows.
    issue = move(logged_in(team.membro), video, issue, "montaggio")
    assert Issue.objects.get(pk=cover.pk).target_date == issue.target_date
    # A cover never gets a cover of its own.
    assert not Issue.issue_objects.filter(parent=cover).exists()


@pytest.mark.contract
@pytest.mark.django_db
def test_the_kind_of_work_can_be_changed(team, video):
    member = logged_in(team.membro)
    issue = make_issue(video.project, video.states["script"])
    url = f"{video.atlante}/issues/{issue.id}/scelte/"
    assert member.patch(url, {"tipo": "carosello"}, format="json").data["work_type"] == "carosello"
    assert member.patch(url, {"tipo": "podcast"}, format="json").status_code == 400
    assert member.patch(url, {"tipo": None}, format="json").data["work_type"] is None


@pytest.mark.contract
@pytest.mark.django_db
def test_new_phases_of_a_template_are_added_when_applied_again(team, video):
    PhaseBinding.objects.filter(project=video.project, phase="grafica_copertina").delete()
    admin = logged_in(team.admin)
    assert admin.get(f"{video.atlante}/modello/").data["missing_phases"] == ["Copertina in grafica"]
    assert admin.post(f"{video.atlante}/modello/", {"template": "video"}, format="json").data["missing_phases"] == []


# The monthly report (release 0.3)


@pytest.mark.contract
@pytest.mark.django_db
def test_the_monthly_report_task_of_every_social_project(team, video):
    from plane.atlante.monthly_reports import REPORT_SECTIONS, create_monthly_reports

    other, _ = make_project(team.ws, "SITO", [(team.admin, ADMIN)])
    apply_template(other, "sito")  # not a social project
    assert create_monthly_reports(date(2026, 11, 2)) == 1
    report = Issue.issue_objects.get(project=video.project, atlante_task_type__kind="report")
    assert report.name == "Report mensile: ottobre 2026"
    assert executors(report) == {video.giulia.id}  # the social media manager
    assert report.target_date == date(2026, 11, 9)  # 5 working days from Monday 2 November
    assert all(section in report.description_html for section in REPORT_SECTIONS)
    assert report.state_id == video.states["da_pianificare"].id
    assert not Issue.issue_objects.filter(parent=report).exists()  # a report has no cover
    # Once a month: running it again creates nothing.
    assert create_monthly_reports(date(2026, 11, 3)) == 0
    assert create_monthly_reports(date(2027, 1, 1)) == 1  # the report of December 2026


@pytest.mark.contract
@pytest.mark.django_db
def test_who_comes_next_gets_a_notice(team, video):
    """Request 11: the new executor gets the notice in the inbox, the person who moved the task does not."""
    member = logged_in(team.membro)
    issue, _ = create(member, video)
    issue = move(member, video, issue, "da_girare")
    notices = Notification.objects.filter(entity_identifier=issue.id, data__issue_activity__field="atlante_phase")
    assert {n.receiver_id for n in notices} >= {video.daniele.id, video.virginia.id}
    assert team.membro.id not in {n.receiver_id for n in notices}
    assert notices.first().triggered_by.email == AUTOMATION_EMAIL

    # Nobody in the role: the responsible person is told that the task is to assign.
    ProjectRole.objects.filter(project=video.project, role="lead_videomaker").delete()
    move(member, video, issue, "girato")
    told = Notification.objects.filter(entity_identifier=issue.id, data__issue_activity__field="atlante_to_assign")
    assert [n.receiver_id for n in told] == [video.davide.id]
