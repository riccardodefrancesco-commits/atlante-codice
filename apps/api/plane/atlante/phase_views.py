# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Templates, roles and task choices (assaggio B): the same rules for the interface
(session login) and the public API (personal API key), written once in the *Handlers classes.

Rules:
- project members see the template, the roles and the choices of a task; guests never do;
- only project admins apply a template and put people in the roles of the project;
- members choose on a task the responsible person, the reviewers, the editor and the dates;
- nothing is deleted: a template renames, recolors and adds states, and links rows only.
"""

import uuid
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.api.views.base import BaseAPIView as PublicBaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.app.views.base import BaseAPIView
from plane.atlante import approvals
from plane.atlante.models import (
    ClientApproval,
    PhaseBinding,
    PhaseEntry,
    ProjectRole,
    ProjectTemplate,
    TaskDate,
    TaskRole,
    TaskType,
)
from plane.atlante.phases import (
    apply_template,
    describe_executor,
    describe_rule,
    is_to_assign,
    italian_date,
    people_names,
    person_name,
    phase_of,
    refresh_phase,
    responsible,
    team_members,
    today,
)
from plane.atlante.project_templates import (
    DATE_PHRASES,
    DATES,
    RESPONSIBLE,
    ROLES,
    TASK_ROLE_NAMES,
    TEMPLATES,
    WORK_TYPES,
    task_dates,
    task_roles,
)
from plane.db.models import Issue, IssueActivity, Project, ProjectMember, WorkspaceMember

PROJECT_NOT_FOUND = {"error": "Progetto non trovato."}
TASK_NOT_FOUND = {"error": "Task non trovata."}


def _project(slug, project_id):
    return Project.objects.filter(workspace__slug=slug, pk=project_id).first()


def _template_of(project_id):
    key = ProjectTemplate.objects.filter(project_id=project_id).values_list("template", flat=True).first()
    return TEMPLATES.get(key)


def project_payload(project):
    template = _template_of(project.id)
    members = {}
    for row in ProjectRole.objects.filter(project=project).order_by("created_at"):
        members.setdefault(row.role, []).append(str(row.member_id))
    role_keys = template.roles if template else tuple(ROLES)
    phases = []
    bindings = PhaseBinding.objects.filter(project=project, state__deleted_at__isnull=True).select_related("state")
    for binding in sorted(bindings, key=lambda b: b.state.sequence):
        source = TEMPLATES.get(binding.template)
        phase = source.phase(binding.phase) if source else None
        if phase is None:
            continue
        phases.append(
            {
                "state_id": str(binding.state_id),
                "phase": phase.key,
                "phase_name": phase.name,
                "executor": phase.executor,
                "executor_name": describe_executor(phase),
                "deadline": describe_rule(phase.deadline),
            }
        )
    bound = {phase["phase"] for phase in phases}
    missing = [phase.name for phase in template.phases if phase.key not in bound] if template else []
    return {
        "project_id": str(project.id),
        "template": template.key if template else None,
        # Phases added to the template after it was applied: applying it again adds them.
        "missing_phases": missing,
        "templates": [{"key": t.key, "name": t.name} for t in TEMPLATES.values()],
        "roles": [{"key": key, "name": ROLES[key], "member_ids": members.get(key, [])} for key in role_keys],
        "phases": phases,
    }


def _is_id(value):
    try:
        uuid.UUID(str(value))
    except ValueError:
        return False
    return isinstance(value, str)


def _member_ids(value):
    """A list of person ids from the request, or None if it is not one."""
    if not isinstance(value, list) or not all(_is_id(item) for item in value):
        return None
    return list(dict.fromkeys(value))


class ProjectTemplateHandlers:
    """GET: template, roles and phases of the project. POST {"template": "video"}: applies the template."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def get(self, request, slug, project_id):
        project = _project(slug, project_id)
        if project is None:
            return Response(PROJECT_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        return Response(project_payload(project), status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN], level="PROJECT")
    def post(self, request, slug, project_id):
        project = _project(slug, project_id)
        if project is None:
            return Response(PROJECT_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        key = request.data.get("template")
        if key not in TEMPLATES:
            return Response({"error": "Modello sconosciuto."}, status=status.HTTP_400_BAD_REQUEST)
        apply_template(project, key)
        return Response(project_payload(project), status=status.HTTP_200_OK)


class ProjectRolesHandlers:
    """PUT {"role": "editor", "member_ids": [...]}: the people of a role in the project.
    It holds for the tasks that enter a phase from now on."""

    @allow_permission([ROLE.ADMIN], level="PROJECT")
    def put(self, request, slug, project_id):
        project = _project(slug, project_id)
        if project is None:
            return Response(PROJECT_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        role = request.data.get("role")
        ids = _member_ids(request.data.get("member_ids"))
        if role not in ROLES or ids is None:
            return Response({"error": "Indica il ruolo e l'elenco delle persone."}, status=status.HTTP_400_BAD_REQUEST)
        if len(team_members(project.id, ids)) != len(ids):
            return Response(
                {"error": "Nei ruoli vanno solo persone del progetto, non ospiti."}, status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            ProjectRole.objects.filter(project=project, role=role).exclude(member_id__in=ids).delete()
            present = {
                str(member_id)
                for member_id in ProjectRole.objects.filter(project=project, role=role).values_list(
                    "member_id", flat=True
                )
            }
            for member_id in ids:
                if member_id not in present:
                    ProjectRole.objects.create(project=project, role=role, member_id=member_id)
        return Response(project_payload(project), status=status.HTTP_200_OK)


def _task(slug, project_id, issue_id):
    return Issue.issue_objects.filter(workspace__slug=slug, project_id=project_id, pk=issue_id).first()


def task_payload(issue):
    template = _template_of(issue.project_id)
    roles = task_roles(template)
    chosen = {}
    for row in TaskRole.objects.filter(issue=issue).order_by("created_at"):
        chosen.setdefault(row.role, []).append(str(row.member_id))
    project_people = {}
    for row in ProjectRole.objects.filter(project_id=issue.project_id, role__in=roles).order_by("created_at"):
        project_people.setdefault(row.role, []).append(str(row.member_id))
    member, source = responsible(issue)
    dates = dict(TaskDate.objects.filter(issue=issue).values_list("kind", "day"))
    _, phase = phase_of(issue.state_id)
    entry = PhaseEntry.objects.filter(issue=issue, state_id=issue.state_id).order_by("-created_at").first()
    return {
        "issue_id": str(issue.id),
        "template": template.key if template else None,
        "responsabile": {"member_id": str(member) if member else None, "source": source},
        "roles": [
            {
                "key": key,
                "name": TASK_ROLE_NAMES.get(key, ROLES[key]),
                "member_ids": chosen.get(key, []),
                "project_member_ids": project_people.get(key, []),
            }
            for key in roles
        ],
        "dates": [
            {"key": key, "name": DATES[key], "day": dates[key].isoformat() if key in dates else None}
            for key in task_dates(template)
        ],
        # Design system, table 14: no executor in a phase that gives the work, no responsible person.
        "to_assign": is_to_assign(issue),
        "work_type": TaskType.objects.filter(issue=issue).values_list("kind", flat=True).first(),
        "work_types": [{"key": key, "name": name} for key, name in WORK_TYPES.items()],
        "phase": (
            {
                "key": phase.key,
                "name": phase.name,
                "executor_name": describe_executor(phase),
                "deadline": describe_rule(phase.deadline),
                "entered_at": entry.created_at.isoformat() if entry else None,
                "rule": entry.rule if entry else "",
            }
            if phase
            else None
        ),
    }


def _record_choice(issue, actor, text):
    """A line in the task history: who changed a choice of the task, and to what."""
    IssueActivity.objects.create(
        issue=issue,
        project_id=issue.project_id,
        workspace_id=issue.workspace_id,
        actor=actor,
        verb="updated",
        field="atlante_task",
        comment=text,
        epoch=int(timezone.now().timestamp()),
    )


def _replace_people(issue, role, ids):
    TaskRole.objects.filter(issue=issue, role=role).exclude(member_id__in=ids).delete()
    present = {str(m) for m in TaskRole.objects.filter(issue=issue, role=role).values_list("member_id", flat=True)}
    for member_id in ids:
        if member_id not in present:
            TaskRole.objects.create(issue=issue, role=role, member_id=member_id)


class TaskChoicesHandlers:
    """GET: responsible person, roles, dates and phase of a task.
    PATCH, any of: {"responsabile": id | null, "<role>": [ids] | null, "<date>": "YYYY-MM-DD" | null}.
    null goes back to the project's choice (or removes the date)."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def get(self, request, slug, project_id, issue_id):
        issue = _task(slug, project_id, issue_id)
        if issue is None:
            return Response(TASK_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        return Response(task_payload(issue), status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def patch(self, request, slug, project_id, issue_id):
        issue = _task(slug, project_id, issue_id)
        if issue is None:
            return Response(TASK_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        template = _template_of(project_id)
        roles = task_roles(template)
        date_kinds = task_dates(template)
        allowed = {RESPONSIBLE, *roles, *date_kinds, "tipo"}
        unknown = [key for key in request.data if key not in allowed]
        if unknown:
            return Response(
                {"error": f"Questa task non ha: {', '.join(sorted(unknown))}."}, status=status.HTTP_400_BAD_REQUEST
            )
        # First every value is checked, then everything is written together.
        people, days = {}, {}
        if RESPONSIBLE in request.data:
            value = request.data[RESPONSIBLE]
            if value is not None and (not _is_id(value) or not team_members(issue.project_id, [value])):
                return Response(
                    {"error": "Il responsabile deve essere una persona del progetto, non un ospite."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            people[RESPONSIBLE] = [value] if value else []
        for role in roles:
            if role not in request.data:
                continue
            ids = [] if request.data[role] is None else _member_ids(request.data[role])
            if ids is None or len(team_members(issue.project_id, ids)) != len(ids):
                return Response(
                    {"error": f"{TASK_ROLE_NAMES.get(role, ROLES[role])}: solo persone del progetto, non ospiti."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            people[role] = ids
        for kind in date_kinds:
            if kind not in request.data:
                continue
            value = request.data[kind]
            try:
                days[kind] = None if value is None else date.fromisoformat(str(value))
            except ValueError:
                return Response(
                    {"error": f"Data {DATE_PHRASES[kind]}: usa il formato AAAA-MM-GG."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        kind = request.data.get("tipo", "") if "tipo" in request.data else ""
        if "tipo" in request.data and kind is not None and kind not in WORK_TYPES:
            return Response({"error": "Tipo di lavoro sconosciuto."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            if "tipo" in request.data:
                if kind is None:
                    TaskType.objects.filter(issue=issue).delete()  # only the link row
                else:
                    TaskType.objects.update_or_create(issue=issue, defaults={"kind": kind})
                _record_choice(issue, request.user, f"Tipo di lavoro: {WORK_TYPES[kind] if kind else 'nessuno'}.")
            for role, ids in people.items():
                _replace_people(issue, role, ids)
            for kind, day in days.items():
                if day is None:
                    TaskDate.objects.filter(issue=issue, kind=kind).delete()  # only the date row
                else:
                    TaskDate.objects.update_or_create(issue=issue, kind=kind, defaults={"day": day})
            for role in people:
                _record_choice(issue, request.user, _choice_sentence(issue, "role", role))
            for kind in days:
                _record_choice(issue, request.user, _choice_sentence(issue, "date", kind))
            for role in people:
                refresh_phase(issue, role=role)
            for kind in days:
                refresh_phase(issue, date_kind=kind)
        return Response(task_payload(issue), status=status.HTTP_200_OK)


def _choice_sentence(issue, what, key):
    if what == "date":
        day = TaskDate.objects.filter(issue=issue, kind=key).values_list("day", flat=True).first()
        return f"Data {DATE_PHRASES[key]}: {italian_date(day) if day else 'tolta'}."
    if key == RESPONSIBLE:
        member, source = responsible(issue)
        who = people_names([member]) if member else "nessuno"
        return f"Responsabile: {who}" + (" (quello del progetto)." if source == "project" else ".")
    ids = list(
        TaskRole.objects.filter(issue=issue, role=key).order_by("created_at").values_list("member_id", flat=True)
    )
    name = TASK_ROLE_NAMES.get(key, ROLES[key])
    return f"{name}: {people_names(ids)}." if ids else f"{name}: quelli del progetto."


def _iso(value):
    return value.isoformat() if value else None


def approval_payload(issue):
    """The client's approval of the task, for the box under the title (design system, table 15)."""
    approval = (
        ClientApproval.objects.filter(issue=issue)
        .exclude(status=ClientApproval.PASSED)
        .select_related("state", "next_state", "decided_by", "sent_by")
        .order_by("-created_at")
        .first()
    )
    if approval is None:
        return {"approval": None}
    client = approvals.client_of(issue)
    is_open = approval.status in approvals.OPEN
    day = today()
    return {
        "approval": {
            "status": approval.status,
            "consent": approval.consent,
            "phase_name": approval.state.name if approval.state else approval.phase,
            "sent_on": _iso(approval.sent_on),
            "sent_by": person_name(approval.sent_by) if approval.sent_by else None,
            "reminder_on": _iso(approval.reminder_on),
            "due_on": _iso(approval.due_on),
            "days_left": (approval.due_on - day).days if approval.due_on else None,
            "reminder_day": bool(approval.reminder_on and day >= approval.reminder_on),
            # From the sixteenth day: silent consent to confirm, or an explicit yes that is late.
            "to_confirm": approvals.silent_consent_due(approval, day),
            "late": bool(approval.due_on and approval.consent and day > approval.due_on),
            # The first day of the silent consent, and the phase an approval leads to.
            "approved_from": _iso(approval.due_on + timedelta(days=1)) if approval.due_on else None,
            "approve_to": approvals.approval_target_name(issue, approval) if is_open else None,
            "round": approval.round,
            "included": approvals.included_rounds(issue),
            "used": approvals.used_rounds(issue),
            "counts_round": approval.counts_round,
            "note": approval.note,
            "decided_at": _iso(approval.decided_at),
            "decided_by": person_name(approval.decided_by) if approval.decided_by else None,
            "next_state_name": approval.next_state.name if approval.next_state else None,
            "client_name": client.name if client else None,
            # Shown while the work is ready or waits in its phase, and after the answer in the phase it led to.
            "visible": (is_open and approval.state_id == issue.state_id)
            or (not is_open and approval.next_state_id == issue.state_id),
        }
    }


OUTCOMES = ("inviata", "approvata", "modifiche", "silenzio_assenso")


class TaskApprovalHandlers:
    """GET: the client's approval of the task. POST {"esito": ...}, recorded by the team until the portal:
    "inviata" (the work was sent: the 15 days start), "approvata", "modifiche" (with "nota" and "conta"),
    "silenzio_assenso" (from the sixteenth day, the silent consent confirmed by a person)."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def get(self, request, slug, project_id, issue_id):
        issue = _task(slug, project_id, issue_id)
        if issue is None:
            return Response(TASK_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        return Response(approval_payload(issue), status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def post(self, request, slug, project_id, issue_id):
        issue = _task(slug, project_id, issue_id)
        if issue is None:
            return Response(TASK_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        outcome = request.data.get("esito")
        if outcome not in OUTCOMES:
            return Response(
                {"error": "Indica l'esito: inviata, approvata, modifiche o silenzio_assenso."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        approval = approvals.open_approval(issue)
        if approval is None or approval.state_id != issue.state_id:
            return Response({"error": "Questa task non aspetta il cliente."}, status=status.HTTP_400_BAD_REQUEST)
        ready = approval.status == ClientApproval.READY
        if outcome == "inviata":
            if not ready:
                return Response(
                    {"error": "Il lavoro è già stato inviato al cliente."}, status=status.HTTP_400_BAD_REQUEST
                )
            approvals.send(issue, approval, request.user)
            return Response(approval_payload(issue), status=status.HTTP_200_OK)
        if ready:
            return Response(
                {"error": 'Prima va inviato al cliente: premi "Inviato al cliente".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if outcome == "silenzio_assenso" and not approvals.silent_consent_due(approval):
            why = (
                "Per questo lavoro serve il sì del cliente: niente silenzio-assenso."
                if approval.consent
                else "Il cliente ha ancora tempo per rispondere."
            )
            return Response({"error": why}, status=status.HTTP_400_BAD_REQUEST)
        note = str(request.data.get("nota") or "")[:2000]
        approvals.decide(
            issue,
            approval,
            approved=outcome != "modifiche",
            user=request.user,
            note=note,
            counts=request.data.get("conta", True) is not False,
            silent=outcome == "silenzio_assenso",
        )
        return Response(approval_payload(Issue.issue_objects.get(pk=issue.pk)), status=status.HTTP_200_OK)


HOME_LIMIT = 50


def _home_row(issue):
    return {
        "id": str(issue.id),
        "name": issue.name,
        "sequence_id": issue.sequence_id,
        "project_id": str(issue.project_id),
        "project_identifier": issue.project.identifier,
        "state_name": issue.state.name if issue.state else None,
        "state_color": issue.state.color if issue.state else None,
        "target_date": issue.target_date.isoformat() if issue.target_date else None,
    }


def home_tasks(user, slug):
    """For the Home (design system, table 14): the tasks to assign that the person is responsible for
    and, for workspace admins, the open tasks of template projects without a responsible person."""
    project_ids = list(
        ProjectMember.objects.filter(
            member=user, workspace__slug=slug, is_active=True, role__gte=ROLE.MEMBER.value
        ).values_list("project_id", flat=True)
    )
    templated = set(ProjectTemplate.objects.filter(project_id__in=project_ids).values_list("project_id", flat=True))
    giving_work = []
    for binding in PhaseBinding.objects.filter(project_id__in=templated, state__deleted_at__isnull=True):
        source = TEMPLATES.get(binding.template)
        phase = source.phase(binding.phase) if source else None
        if phase is not None and phase.executor:
            giving_work.append(binding.state_id)
    issues = Issue.issue_objects.filter(project_id__in=templated).select_related("project", "state")
    chosen = dict(
        TaskRole.objects.filter(issue__project_id__in=templated, role=RESPONSIBLE).values_list("issue_id", "member_id")
    )
    accounts = {}
    for row in ProjectRole.objects.filter(project_id__in=templated, role="account").order_by("created_at"):
        accounts.setdefault(row.project_id, row.member_id)

    def responsible_of(issue):
        return chosen.get(issue.id) or accounts.get(issue.project_id)

    to_assign = (
        issues.filter(state_id__in=giving_work)
        .annotate(executors=Count("issue_assignee", filter=Q(issue_assignee__deleted_at__isnull=True)))
        .filter(executors=0)
        .order_by("target_date", "-created_at")
    )
    mine = [_home_row(issue) for issue in to_assign if responsible_of(issue) == user.id][:HOME_LIMIT]
    waiting = (
        ClientApproval.objects.filter(status__in=approvals.OPEN, issue__project_id__in=project_ids)
        .select_related("issue", "issue__project", "issue__state")
        .order_by("status", "due_on")
    )
    asked = []
    for approval in waiting:
        issue = approval.issue
        if issue.deleted_at or issue.archived_at or approval.state_id != issue.state_id:
            continue
        member = chosen.get(issue.id) or accounts.get(issue.project_id)
        if member != user.id:
            continue
        client = approvals.client_of(issue)
        asked.append(
            {
                **_home_row(issue),
                "ready": approval.status == ClientApproval.READY,
                "days_left": (approval.due_on - today()).days if approval.due_on else None,
                "reminder_day": bool(approval.reminder_on and today() >= approval.reminder_on),
                "to_confirm": approvals.silent_consent_due(approval),
                "consent": approval.consent,
                "client_code": client.code if client else None,
                "client_color": client.color if client else None,
            }
        )
    result = {"to_assign": mine, "without_responsible": None, "approvals": asked[:HOME_LIMIT]}
    if WorkspaceMember.objects.filter(
        member=user, workspace__slug=slug, role=ROLE.ADMIN.value, is_active=True
    ).exists():
        open_issues = issues.exclude(state__group__in=("completed", "cancelled")).order_by("-created_at")
        result["without_responsible"] = [_home_row(issue) for issue in open_issues if responsible_of(issue) is None][
            :HOME_LIMIT
        ]
    return result


class TemplatesHandlers:
    """GET: the project templates, to choose one when a project is created."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        return Response([{"key": t.key, "name": t.name} for t in TEMPLATES.values()], status=status.HTTP_200_OK)


class HomeTasksHandlers:
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        return Response(home_tasks(request.user, slug), status=status.HTTP_200_OK)


# Interface endpoints (session login), under /api/atlante/


class HomeTasksEndpoint(HomeTasksHandlers, BaseAPIView):
    pass


class TaskApprovalEndpoint(TaskApprovalHandlers, BaseAPIView):
    pass


class TemplatesEndpoint(TemplatesHandlers, BaseAPIView):
    pass


class ProjectTemplateEndpoint(ProjectTemplateHandlers, BaseAPIView):
    pass


class ProjectRolesEndpoint(ProjectRolesHandlers, BaseAPIView):
    pass


class TaskChoicesEndpoint(TaskChoicesHandlers, BaseAPIView):
    pass


# Public API endpoints (personal API key), under /api/v1/atlante/


class PublicProjectTemplateEndpoint(ProjectTemplateHandlers, PublicBaseAPIView):
    pass


class PublicProjectRolesEndpoint(ProjectRolesHandlers, PublicBaseAPIView):
    pass


class PublicTaskChoicesEndpoint(TaskChoicesHandlers, PublicBaseAPIView):
    pass


class PublicHomeTasksEndpoint(HomeTasksHandlers, PublicBaseAPIView):
    pass


class PublicTaskApprovalEndpoint(TaskApprovalHandlers, PublicBaseAPIView):
    pass
