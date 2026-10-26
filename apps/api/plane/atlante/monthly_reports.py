# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The monthly report as a tracked task (docs/specifica/11-dai-vecchi-programmi.md, section 3): on the
first day of every month, in every social project, a task for the report of the month just ended, with
the list of the sections to prepare, for the social media manager.

The sections are a proposal, to check with the report of today's client portal (not in this repository).
"""

from html import escape

from django.db import transaction

from plane.atlante.models import PhaseBinding, ProjectTemplate, TaskType
from plane.atlante.phases import MONTHS, enter_phase, people_in_role, team_members, today, _set_executors
from plane.atlante.working_days import add_working_days
from plane.db.models import Issue, State

REPORT_SECTIONS = (
    "Numeri del mese per canale",
    "Contenuti migliori del mese",
    "Crescita del pubblico",
    "Risultati delle campagne ADV, se attive",
    "Cosa faremo il mese prossimo",
)
SOCIAL_TEMPLATES = ("post", "video")
REPORT_DAYS = 5  # working days to prepare it (proposal)


def report_name(day):
    month = day.month - 1 or 12
    year = day.year if day.month > 1 else day.year - 1
    return f"Report mensile: {MONTHS[month - 1]} {year}"


def _start_state(project):
    """The first phase of the project, without rules: the report has its own executor and delivery date."""
    binding = PhaseBinding.objects.filter(project=project, phase="da_pianificare").select_related("state").first()
    if binding is not None:
        return binding.state
    return State.objects.filter(project=project, group="backlog").order_by("sequence").first()


def create_monthly_reports(day=None):
    """Creates the report task of the month just ended in every social project. Returns how many were
    created: a project that already has it is skipped."""
    day = day or today()
    created = 0
    for link in ProjectTemplate.objects.filter(template__in=SOCIAL_TEMPLATES, project__archived_at__isnull=True):
        if create_report(link.project, day) is not None:
            created += 1
    return created


def create_report(project, day):
    """The report task of the month before `day` in one project, or None if the project has it."""
    name = report_name(day)
    if Issue.issue_objects.filter(project=project, name=name, atlante_task_type__kind="report").exists():
        return None
    with transaction.atomic():
        sections = "".join(f"<li><p>{escape(section)}</p></li>" for section in REPORT_SECTIONS)
        report = Issue.objects.create(
            project=project,
            workspace_id=project.workspace_id,
            name=name,
            state=_start_state(project),
            priority="medium",
            target_date=add_working_days(day, REPORT_DAYS),
            description_html=f"<p>Le sezioni da preparare:</p><ul>{sections}</ul>",
        )
        TaskType.objects.create(issue=report, kind="report")
        ids, _ = people_in_role(report, "social_media_manager")
        _set_executors(report, team_members(project.id, ids))
        enter_phase(report, created=True)
    return report
