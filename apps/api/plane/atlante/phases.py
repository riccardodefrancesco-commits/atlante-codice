# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The phase rules (request 34) and the urgency (section 9 of the specification).

- When a task enters a phase, the phase's role picks the executor (Plane's assignees) and the
  delivery date, "Consegna" (Plane's target date). Nobody in the role: the task has no executor,
  it is "Da assegnare" and the people of the phase before do not keep it.
- The urgency days start the day someone is assigned, by a rule or by hand, in every project:
  Urgente 1, Prioritario 3, Standard 7, In blocco 10 working days. Changing the urgency counts
  again from that day.

The rules find the phase through PhaseBinding, so the name, color, group and order of the state
never matter. Every entry goes to PhaseEntry; what a rule did goes to the task history with the
"Atlante" automation as the author.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import timedelta
from zoneinfo import ZoneInfo

from crum import get_current_user
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from plane.atlante.models import (
    PhaseBinding,
    PhaseEntry,
    ProjectRole,
    ProjectTemplate,
    TaskAssignment,
    TaskDate,
    TaskRole,
    TaskType,
)
from plane.atlante.project_templates import (
    DATE_PHRASES,
    RESPONSIBLE,
    RESPONSIBLE_ROLE,
    ROLES,
    TEMPLATES,
    URGENCY,
)
from plane.atlante.working_days import add_working_days
from plane.db.models import Issue, IssueActivity, IssueAssignee, Notification, ProjectMember, State, User

ROME = ZoneInfo("Europe/Rome")
MONTHS = (
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
)
# The author of the automatic lines in the history. ".invalid" is a reserved domain: no mail goes there.
AUTOMATION_EMAIL = "automazioni@atlante.invalid"
TEAM_ROLE = 15  # project members and admins; guests never do the work
SEQUENCE_START, SEQUENCE_STEP = 15000, 10000
# Only while invented data are prepared (atlante_dati_collaudo): the day the rules count from.
_PREPARED_DAY = ContextVar("atlante_prepared_day", default=None)


def today():
    return _PREPARED_DAY.get() or timezone.localtime(timezone.now(), ROME).date()


@contextmanager
def as_on(day):
    """The rules run as if today were `day`: invented data with their history in the past."""
    token = _PREPARED_DAY.set(day)
    try:
        yield
    finally:
        _PREPARED_DAY.reset(token)


def italian_date(day):
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def working_days(n):
    return "1 giorno lavorativo" if n == 1 else f"{n} giorni lavorativi"


def calendar_days(n):
    return "1 giorno di calendario" if n == 1 else f"{n} giorni di calendario"


def person_name(user):
    full = f"{user.first_name} {user.last_name}".strip()
    return full or user.display_name or user.email


def automation_user():
    """The "Atlante" bot: it cannot sign in (inactive, no password) and is nobody's colleague."""
    user = User.objects.filter(email=AUTOMATION_EMAIL).first()
    if user is None:
        user = User(
            email=AUTOMATION_EMAIL,
            username="atlante-automazioni",
            first_name="Atlante",
            display_name="Atlante",
            is_bot=True,
            bot_type="atlante",
            is_active=False,
        )
        user.set_unusable_password()
        user.save()
    return user


# Applying a template to a project


def _free_name(project, name):
    candidate, number = name, 2
    while State.all_state_objects.filter(project=project, name__iexact=candidate, deleted_at__isnull=True).exists():
        candidate, number = f"{name} {number}", number + 1
    return candidate


def apply_template(project, key):
    """Gives the project the phases of a template. Nothing is deleted:
    - a phase already bound keeps its state as the admins left it;
    - an unbound state with the same name, or of the same group and without tasks, is reused;
    - otherwise a new state is created.
    The other states stay as they are, without rules."""
    template = TEMPLATES[key]
    with transaction.atomic():
        ProjectTemplate.objects.update_or_create(project=project, defaults={"template": key})
        PhaseBinding.objects.filter(project=project).exclude(template=key).delete()  # only the links
        bound = {
            binding.phase: binding
            for binding in PhaseBinding.objects.filter(project=project, state__deleted_at__isnull=True)
        }
        PhaseBinding.objects.filter(project=project).exclude(pk__in=[b.pk for b in bound.values()]).delete()
        states = list(State.objects.filter(project=project).order_by("sequence"))
        used = {binding.state_id for binding in bound.values()}
        with_tasks = set(Issue.all_objects.filter(project=project).values_list("state_id", flat=True).distinct())
        default_state = None
        for index, phase in enumerate(template.phases):
            if phase.key in bound:
                continue
            same_name = [s for s in states if s.id not in used and s.name.casefold() == phase.name.casefold()]
            same_group = [s for s in states if s.id not in used and s.group == phase.group and s.id not in with_tasks]
            sequence = SEQUENCE_START + index * SEQUENCE_STEP
            if same_name:
                state = same_name[0]
            elif same_group:
                state = same_group[0]
                state.name = _free_name(project, phase.name) if state.name != phase.name else phase.name
                state.color = phase.color
                state.save()
            else:
                state = State.objects.create(
                    project=project,
                    workspace=project.workspace,
                    name=_free_name(project, phase.name),
                    color=phase.color,
                    group=phase.group,
                )
            # The order of the template; save() would always put a new state at the end.
            State.objects.filter(pk=state.pk).update(sequence=sequence)
            used.add(state.id)
            PhaseBinding.objects.create(state=state, project=project, template=key, phase=phase.key)
            if phase.default:
                default_state = state
        if default_state is not None:
            State.objects.filter(project=project).exclude(pk=default_state.pk).update(default=False)
            State.objects.filter(pk=default_state.pk).update(default=True)


# Who and when


def responsible(issue):
    """(member id, "task" | "project" | None): the person chosen on the task, otherwise the project's account."""
    chosen = TaskRole.objects.filter(issue=issue, role=RESPONSIBLE).values_list("member_id", flat=True).first()
    if chosen:
        return chosen, "task"
    account = (
        ProjectRole.objects.filter(project_id=issue.project_id, role=RESPONSIBLE_ROLE)
        .order_by("created_at")
        .values_list("member_id", flat=True)
        .first()
    )
    return (account, "project") if account else (None, None)


def people_in_role(issue, role):
    """(member ids, "task" | "project"): the people chosen on the task for the role, otherwise the project's."""
    if role == RESPONSIBLE:
        member, source = responsible(issue)
        return ([member] if member else []), source
    chosen = list(
        TaskRole.objects.filter(issue=issue, role=role).order_by("created_at").values_list("member_id", flat=True)
    )
    if chosen:
        return chosen, "task"
    return (
        list(
            ProjectRole.objects.filter(project_id=issue.project_id, role=role)
            .order_by("created_at")
            .values_list("member_id", flat=True)
        ),
        "project",
    )


def team_members(project_id, ids):
    """Only active members of the project, never guests, in the given order (ids as given)."""
    active = {
        str(member_id)
        for member_id in ProjectMember.objects.filter(
            project_id=project_id, member_id__in=ids, is_active=True, role__gte=TEAM_ROLE
        ).values_list("member_id", flat=True)
    }
    return [member_id for member_id in ids if str(member_id) in active]


def _executors(issue, phase):
    """(member ids, sentence about where they come from): the people of the phase's role, otherwise
    of its fallback role; an empty list when there is nobody."""
    for role in (phase.executor, phase.fallback):
        if role is None:
            continue
        ids, source = people_in_role(issue, role)
        ids = team_members(issue.project_id, ids)
        if not ids:
            continue
        if role == RESPONSIBLE:
            why = "il responsabile della task"
            if role != phase.executor:
                why += f": nessuno nel ruolo {ROLES.get(phase.executor, phase.executor)}"
        else:
            why = "scelto sulla task" if source == "task" else f"ruolo {ROLES.get(role, role)} del progetto"
        return ids, why
    return [], ""


def people_names(ids):
    people = {str(user.id): person_name(user) for user in User.objects.filter(id__in=ids)}
    return ", ".join(people[str(member_id)] for member_id in ids if str(member_id) in people)


def urgency_of(issue):
    """(name, working days) of the task's urgency."""
    return URGENCY.get(issue.priority or "none", URGENCY["none"])


def _urgency(issue, assigned_on):
    """(date, sentence); the date is None for a task without urgency: its delivery date is set by hand."""
    name, days = urgency_of(issue)
    if days is None:
        return None, "la task non ha urgenza"
    return add_working_days(assigned_on, days), f"{name}: {working_days(days)} dall'assegnazione"


# Deadline rules that count from the day someone is assigned: they wait while nobody is.
WAITING = ("urgenza", "lavorativi")
# Outside a template phase the urgency sets the delivery date, but not for closed tasks.
URGENCY_RULE = ("urgenza",)
CLOSED_GROUPS = ("completed", "cancelled")


def _deadline(issue, rule, start):
    """(date, sentence) for a deadline rule. start: the day of the assignment for the rules that
    wait for it, otherwise the day the task entered the phase."""
    kind = rule[0]
    if kind == "urgenza":
        return _urgency(issue, start)
    if kind == "padre":
        parent = Issue.all_objects.filter(pk=issue.parent_id).values_list("target_date", flat=True).first()
        if parent:
            return parent, "la consegna del video"
        deadline, why = _urgency(issue, start)
        return deadline, f"il video non ha ancora una consegna, {why}" if deadline else why
    if kind == "lavorativi":
        return add_working_days(start, rule[1]), f"{working_days(rule[1])} dall'assegnazione"
    if kind == "calendario":
        return start + timedelta(days=rule[1]), f"{calendar_days(rule[1])} per il cliente"
    _, date_kind, offset = rule
    label = DATE_PHRASES[date_kind]
    day = TaskDate.objects.filter(issue=issue, kind=date_kind).values_list("day", flat=True).first()
    if day is None:
        deadline, why = _urgency(issue, start)
        return deadline, f"manca la data {label} e {why}" if deadline is None else f"manca la data {label}, {why}"
    if offset:
        direction = "prima" if offset < 0 else "dopo"
        return add_working_days(day, offset), f"{working_days(abs(offset))} {direction} della data {label}"
    return day, f"la data {label}"


def describe_rule(rule):
    """The deadline rule in words, for the settings page."""
    if rule is None:
        return "Non cambia"
    kind = rule[0]
    if kind == "urgenza":
        return "Dall'urgenza, in giorni lavorativi dall'assegnazione"
    if kind == "lavorativi":
        return f"{working_days(rule[1])} dall'assegnazione"
    if kind == "calendario":
        return f"{calendar_days(rule[1])} per il cliente"
    if kind == "padre":
        return "La consegna del video"
    _, date_kind, offset = rule
    label = DATE_PHRASES[date_kind]
    if offset:
        direction = "prima" if offset < 0 else "dopo"
        return f"{working_days(abs(offset))} {direction} della data {label}"
    return f"La data {label}"


def describe_executor(phase):
    if phase.executor is None:
        return "Non cambia"
    name = "Responsabile della task" if phase.executor == RESPONSIBLE else ROLES.get(phase.executor, phase.executor)
    if phase.fallback == RESPONSIBLE:
        name += ", altrimenti il responsabile"
    return name


def _current_executors(issue):
    return list(IssueAssignee.objects.filter(issue=issue).values_list("assignee_id", flat=True))


def _set_executors(issue, ids):
    """Returns True if the executors changed. An empty list leaves the task without executor."""
    if set(_current_executors(issue)) == set(ids):
        return False
    # As Plane does when assignees change: the old rows are soft deleted, the new ones created.
    IssueAssignee.objects.filter(issue=issue).delete()
    user = get_current_user()
    author = user.id if user is not None and not user.is_anonymous else issue.created_by_id
    IssueAssignee.objects.bulk_create(
        [
            IssueAssignee(
                assignee_id=member_id,
                issue=issue,
                project_id=issue.project_id,
                workspace_id=issue.workspace_id,
                created_by_id=author,
                updated_by_id=author,
            )
            for member_id in ids
        ],
        batch_size=10,
        ignore_conflicts=True,
    )
    return True


def _set_deadline(issue, day):
    Issue.all_objects.filter(pk=issue.pk).update(target_date=day, updated_at=timezone.now())
    issue.target_date = day


def _record(issue, state_name, text):
    IssueActivity.objects.create(
        issue=issue,
        project_id=issue.project_id,
        workspace_id=issue.workspace_id,
        actor=automation_user(),
        verb="updated",
        field="atlante_phase",
        new_value=state_name,
        comment=text,
        epoch=int(timezone.now().timestamp()),
    )


def _notify(issue, receivers, field, state_name, text):
    """Request 11: who comes next gets a notice in the inbox (Plane's notifications). Not the person who
    moved the task: they already know."""
    user = get_current_user()
    mover = user.id if user is not None and not user.is_anonymous else None
    receivers = [member_id for member_id in dict.fromkeys(receivers) if member_id and member_id != mover]
    if not receivers:
        return
    bot = automation_user()
    project = issue.project
    state = State.all_state_objects.filter(pk=issue.state_id).values("name", "group").first() or {}
    Notification.objects.bulk_create(
        [
            Notification(
                workspace_id=issue.workspace_id,
                project_id=issue.project_id,
                receiver_id=member_id,
                triggered_by=bot,
                sender="in_app:issue_activities:assigned",
                entity_identifier=issue.id,
                entity_name="issue",
                title=text,
                data={
                    "issue": {
                        "id": str(issue.id),
                        "name": issue.name,
                        "identifier": project.identifier,
                        "sequence_id": issue.sequence_id,
                        "state_name": state.get("name"),
                        "state_group": state.get("group"),
                    },
                    "issue_activity": {
                        "id": None,
                        "verb": "updated",
                        "field": field,
                        "actor": str(bot.id),
                        "new_value": state_name,
                        "old_value": "",
                        "issue_comment": "",
                        "old_identifier": None,
                        "new_identifier": None,
                    },
                },
            )
            for member_id in receivers
        ]
    )


def _tell_who_comes_next(issue, before, after, text):
    """The new executors get the task; with nobody, the responsible person has a task to assign."""
    state_name = _state_name(issue)
    if after:
        added = [member_id for member_id in after if member_id not in set(before)]
        _notify(issue, added, "atlante_phase", state_name, text)
    else:
        member, _ = responsible(issue)
        _notify(issue, [member], "atlante_to_assign", state_name, text)


def phase_of(state_id):
    """(template, phase) of a state, or (None, None) for a state without a phase role."""
    binding = PhaseBinding.objects.filter(state_id=state_id).only("template", "phase").first()
    template = TEMPLATES.get(binding.template) if binding else None
    phase = template.phase(binding.phase) if template else None
    return (template, phase) if phase else (None, None)


def deadline_rule(issue):
    """The rule that sets the delivery date now: the phase's, or the urgency outside a template."""
    _, phase = phase_of(issue.state_id)
    if phase is not None:
        return phase.deadline
    group = State.all_state_objects.filter(pk=issue.state_id).values_list("group", flat=True).first()
    return None if group in CLOSED_GROUPS else URGENCY_RULE


def is_to_assign(issue):
    """The task is in a phase whose role gives the work, and nobody has it: "Da assegnare"."""
    _, phase = phase_of(issue.state_id)
    return bool(phase and phase.executor) and not IssueAssignee.objects.filter(issue=issue).exists()


def _assignment(issue):
    assignment, _ = TaskAssignment.objects.get_or_create(
        issue=issue, defaults={"assigned_on": None, "priority": issue.priority or ""}
    )
    return assignment


def _state_name(issue):
    return State.all_state_objects.filter(pk=issue.state_id).values_list("name", flat=True).first()


def _executor_sentence(before, after, phase_name, role, why):
    if not after:
        missing = "Manca il responsabile" if role == RESPONSIBLE else f"Nessuno nel ruolo {ROLES.get(role, role)}"
        tail = " e chi ci lavorava prima non la tiene" if before else ""
        return f"{missing}: la task è da assegnare{tail}."
    names = people_names(after)
    if not before:
        return f"Esecutore: {names}, con la fase {phase_name} ({why})."
    if set(before) == set(after):
        return f"L'esecutore resta {names} con la fase {phase_name} ({why})."
    return f"L'esecutore è passato da {people_names(before)} a {names} con la fase {phase_name} ({why})."


def enter_phase(issue, created=False):
    """The task has just entered its state, or was created. On creation what the person chose in the
    form (executor, delivery date) stays. Outside a template phase only the urgency counts."""
    from plane.atlante.approvals import phase_entered  # here: approvals uses this module

    template, phase = phase_of(issue.state_id)
    if created:
        _give_work_type(issue, template)
    phase_entered(issue, phase)
    if phase is None:
        if created:
            _created_outside_template(issue)
        return None
    day, parts = today(), []
    assignment = _assignment(issue)
    before = _current_executors(issue)
    if phase.executor:
        if created and before:
            parts.append("Esecutore: scelto alla creazione.")
            after = before
        else:
            after, why = _executors(issue, phase)
            _set_executors(issue, after)
            parts.append(_executor_sentence(before, after, _state_name(issue), phase.executor, why))
            _tell_who_comes_next(issue, before, after, parts[-1])
        assignment.assigned_on = day if after else None
    elif created and before:
        assignment.assigned_on = day
    if phase.deadline:
        waiting = phase.deadline[0] in WAITING
        if created and issue.target_date:
            parts.append("Consegna: scelta alla creazione.")
        elif waiting and assignment.assigned_on is None:
            _set_deadline(issue, None)
            parts.append("La consegna si calcola quando qualcuno viene assegnato.")
        else:
            due, why = _deadline(issue, phase.deadline, assignment.assigned_on if waiting else day)
            if due is None:
                parts.append(f"Consegna: invariata, {why}.")
            else:
                _set_deadline(issue, due)
                parts.append(f"Consegna: {italian_date(due)} ({why}).")
    assignment.priority = issue.priority or ""
    assignment.save()
    entry = PhaseEntry.objects.create(
        issue=issue,
        state_id=issue.state_id,
        phase=phase.key,
        deadline=issue.target_date if phase.deadline else None,
        executor_ids=[str(member_id) for member_id in _current_executors(issue)],
        rule=" ".join(parts),
    )
    if parts:
        _record(issue, _state_name(issue), " ".join(parts))
    _covers_follow(issue)
    if created and template.cover_phase and issue.parent_id is None and work_type(issue) == template.work_type:
        create_cover(issue, template)
    return entry


def work_type(issue):
    return TaskType.objects.filter(issue=issue).values_list("kind", flat=True).first()


def _give_work_type(issue, template):
    """A new task gets the kind of work of its template, if it has none yet."""
    if template is not None and not TaskType.objects.filter(issue=issue).exists():
        TaskType.objects.create(issue=issue, kind=template.work_type)


def create_cover(video, template):
    """Request 36: with a video, its cover. A sub-task of the video, in the cover phase, for the
    graphic designer of the project, with the names of the videomakers to ask for information."""
    binding = PhaseBinding.objects.filter(project_id=video.project_id, phase=template.cover_phase).first()
    if binding is None:
        return None
    videomakers = people_names(team_members(video.project_id, people_in_role(video, "videomaker")[0]))
    code = f"{video.project.identifier}-{video.sequence_id}"
    cover = Issue.objects.create(
        project_id=video.project_id,
        workspace_id=video.workspace_id,
        name=f"Copertina: {video.name}",
        parent=video,
        state_id=binding.state_id,
        priority=video.priority,
        description_html=(
            f"<p>Copertina del video {code}. Per le informazioni chiedi a chi fa le riprese: "
            f"{videomakers or 'il videomaker non è ancora scelto nel progetto'}.</p>"
        ),
    )
    TaskType.objects.create(issue=cover, kind="copertina")
    enter_phase(cover, created=True)
    _record(
        video, _state_name(video), f"Creata la task della copertina: {video.project.identifier}-{cover.sequence_id}."
    )
    return cover


def _covers_follow(video):
    """The covers still waiting for their graphics have the same delivery date as their video."""
    for cover in Issue.issue_objects.filter(parent=video):
        _, phase = phase_of(cover.state_id)
        if phase is not None and phase.deadline == ("padre",) and cover.target_date != video.target_date:
            if video.target_date is not None:
                _set_deadline(cover, video.target_date)
                _record(cover, _state_name(cover), f"Consegna: {italian_date(video.target_date)}, come il video.")


def _created_outside_template(issue):
    """A task created outside a template phase: if it already has an executor, its urgency days start today."""
    assignment = _assignment(issue)
    if _current_executors(issue):
        assignment.assigned_on = today()
        due, why = _deadline(issue, URGENCY_RULE, assignment.assigned_on)
        if not issue.target_date and deadline_rule(issue) and due is not None:
            _set_deadline(issue, due)
            _record(issue, _state_name(issue), f"Consegna: {italian_date(due)} ({why}).")
    assignment.priority = issue.priority or ""
    assignment.save()


def task_saved(issue):
    """After any change that is not a new phase: someone assigned to a task without executor starts
    the urgency days; a new urgency counts the delivery date again from the assignment."""
    assignment = _assignment(issue)
    executors = _current_executors(issue)
    rule = deadline_rule(issue)
    waiting = rule is not None and rule[0] in WAITING
    text = None
    if assignment.assigned_on is None and executors:
        assignment.assigned_on = today()
        due, why = _deadline(issue, rule, assignment.assigned_on) if waiting else (None, "")
        if due is not None:
            _set_deadline(issue, due)
            text = f"Esecutore: {people_names(executors)}. Consegna: {italian_date(due)} ({why})."
    elif assignment.assigned_on is not None and not executors:
        assignment.assigned_on = None
    if (issue.priority or "") != assignment.priority:
        assignment.priority = issue.priority or ""
        if text is None and assignment.assigned_on is not None and rule is not None and rule[0] == "urgenza":
            due, why = _deadline(issue, rule, assignment.assigned_on)
            if due is not None and due != issue.target_date:
                _set_deadline(issue, due)
                text = f"Nuova urgenza. Consegna: {italian_date(due)} ({why})."
    assignment.save()
    if text:
        _record(issue, _state_name(issue), text)
        _covers_follow(issue)


def refresh_phase(issue, *, role=None, date_kind=None):
    """A choice on the task changed (the people of a role, a date): the rule of the current phase runs
    again if it uses that choice."""
    _, phase = phase_of(issue.state_id)
    if phase is None:
        return
    roles = (phase.executor, phase.fallback, RESPONSIBLE)
    people = role is not None and phase.executor is not None and role in roles
    deadline = date_kind is not None and phase.deadline is not None and phase.deadline[:2] == ("data", date_kind)
    parts = []
    if people:
        before = _current_executors(issue)
        after, why = _executors(issue, phase)
        if set(before) != set(after):
            _set_executors(issue, after)
            parts.append(_executor_sentence(before, after, _state_name(issue), phase.executor, why))
            _tell_who_comes_next(issue, before, after, parts[-1])
            assignment = _assignment(issue)
            assignment.assigned_on = (assignment.assigned_on or today()) if after else None
            assignment.save()
            if phase.deadline and phase.deadline[0] in WAITING:
                if not after:
                    _set_deadline(issue, None)
                    parts.append("La consegna si calcola quando qualcuno viene assegnato.")
                elif not before:
                    due, why = _deadline(issue, phase.deadline, assignment.assigned_on)
                    if due is not None:
                        _set_deadline(issue, due)
                        parts.append(f"Consegna: {italian_date(due)} ({why}).")
    if deadline:
        entered = PhaseEntry.objects.filter(issue=issue, state_id=issue.state_id).aggregate(last=Max("created_at"))[
            "last"
        ]
        start = timezone.localtime(entered, ROME).date() if entered else today()
        due, why = _deadline(issue, phase.deadline, start)
        if due is not None and due != issue.target_date:
            _set_deadline(issue, due)
            parts.append(f"Consegna: {italian_date(due)} ({why}).")
    if parts:
        _record(issue, _state_name(issue), "Aggiornato. " + " ".join(parts))
        _covers_follow(issue)
