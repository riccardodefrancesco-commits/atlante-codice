# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Creates "Zeta3 Collaudo", the workspace of the online trial of release 0.3 (zeta3-progetti,
docs/collaudo-0.3.md, section 2): invented clients, colleagues and tasks, with the dates counted from
the day it runs. Never real data of clients, never a copy of another database.

Usage, inside the api container, with the local credentials file on standard input:
    python manage.py atlante_dati_collaudo --persone - < atlante/locale/credenziali-prova.md
    python manage.py atlante_dati_collaudo --persone - --nuovo-giro < ...   # a second round

The four people come from the table under "## Zeta3 Collaudo" in that file (columns Chi, Nome, Email,
Password; Cognome is optional): the passwords are written only there. Who already has an account keeps
it, with their password.

Every task gets to its phase through the phase rules, step by step, on the days of the plan below, as
if the people had done it then: the history says who did what and when. The mornings run the client
approvals job, as the server does. It refuses unless ATLANTE_AMBIENTE=prova and never touches another
workspace: a second round archives the first one (renamed, without members), it does not delete it.
"""

import json
import os
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, time, timedelta
from pathlib import Path

from crum import impersonate
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from plane.atlante import approvals
from plane.atlante.models import (
    Client,
    ClientApproval,
    PhaseBinding,
    PhaseEntry,
    ProjectClient,
    ProjectRole,
    TaskDate,
)
from plane.atlante.monthly_reports import create_report
from plane.atlante.phases import ROME, apply_template, as_on, enter_phase, today as rome_today
from plane.atlante.working_days import add_working_days
from plane.bgtasks.issue_activities_task import issue_activity
from plane.db.models import (
    Issue,
    IssueActivity,
    Notification,
    Profile,
    Project,
    ProjectIdentifier,
    ProjectMember,
    State,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.db.models.state import DEFAULT_STATES
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration

WORKSPACE_SLUG = "zeta3-collaudo"
WORKSPACE_NAME = "Zeta3 Collaudo"
SECTION = "## Zeta3 Collaudo"

ADMIN, MEMBER = 20, 15

# The people of the trial: role in the workspace and job. Names, emails and passwords are in the local file.
PEOPLE = {
    "rick": (ADMIN, "Titolare"),
    "alessandra": (ADMIN, "Project manager e account"),
    "virginia": (MEMBER, "Editor video"),
    "giulia": (MEMBER, "Head social media manager"),
}
# Invented colleagues: they never sign in. Their own domain, so they never meet the people of zeta3-prova.
COLLEAGUES = {
    "dario": ("Dario", "Prova", "Videomaker (inventato)"),
    "carla": ("Carla", "Prova", "Grafica (inventata)"),
}
COLLEAGUES_DOMAIN = "collaudo.esempio.it"

# (name, code, color, revision rounds included in the contract)
CLIENTS = [
    ("Alfa Biscotti", "ALF", "#E5484D", 2),
    ("Zeta Gelati", "ZET", "#0090FF", 2),
]

PROJECT_ADMINS = ("rick", "alessandra")
# (identifier, name, template, people in the roles of the project)
PROJECTS = [
    (
        "ALFV",
        "Alfa Biscotti · Video",
        "video",
        {
            "account": ["alessandra"],
            "project_manager": ["alessandra"],
            "social_media_manager": ["giulia"],
            "lead_videomaker": ["dario"],
            "videomaker": [],
            "editor": ["virginia"],
            "grafico": ["carla"],
            "revisore_interno": ["giulia"],
        },
    ),
    (
        "ALFS",
        "Alfa Biscotti · Social",
        "post",
        {
            "account": ["alessandra"],
            "social_media_manager": ["giulia"],
            "grafico": ["carla"],
            "revisore_interno": ["giulia"],
        },
    ),
]

# What the history of a prepared task says at most: older mornings have nothing left to do.
MORNINGS = 31
MORNING = time(7, 15)  # the approvals job: 05:15 UTC
REPORT_MORNING = time(7, 0)  # the monthly reports job: 05:00 UTC
FIRST_STEP, STEP_GAP = time(9, 0), timedelta(minutes=25)


def _late_montaggio(day):
    """How many days ago a Prioritario task (3 working days) entered "In montaggio" to be due on the
    working day before `day`: late on the day of the trial, by the rules."""
    due = add_working_days(day, -1)
    return (day - add_working_days(due, -3)).days


def plan(day):
    """The tasks of section 2, oldest first: (project, title, urgency, dates in days from `day`, steps).
    A step is (days before `day`, who, what, phase): "crea", "fase" (moves it, as on the board),
    "invia" ("Inviato al cliente") or "approva" (the client's yes, recorded by the person)."""
    chef = _late_montaggio(day)
    return [
        (
            "ALFV",
            "Video intervista al fondatore",
            "high",
            {"riprese": -22, "pubblicazione": 10},
            [
                (30, "alessandra", "crea", None),
                (28, "giulia", "fase", "approvazione_script"),
                (28, "alessandra", "invia", None),
                (26, "alessandra", "approva", None),
                (22, "alessandra", "fase", "girato"),
                (20, "dario", "fase", "montaggio"),
                (17, "virginia", "fase", "revisione_interna"),
                (16, "giulia", "fase", "approvazione_cliente"),
                (16, "alessandra", "invia", None),  # 16 days ago: silent consent to confirm
            ],
        ),
        (
            "ALFV",
            "Reel dietro le quinte",
            "medium",
            {"riprese": -14, "pubblicazione": 14},
            [
                (22, "alessandra", "crea", None),
                (20, "giulia", "fase", "approvazione_script"),
                (20, "alessandra", "invia", None),
                (18, "alessandra", "approva", None),
                (14, "alessandra", "fase", "girato"),
                (12, "dario", "fase", "montaggio"),
                (5, "virginia", "fase", "revisione_interna"),
                (4, "giulia", "fase", "approvazione_cliente"),
                (3, "alessandra", "invia", None),  # 12 days left, round 1 of 2
            ],
        ),
        (
            "ALFV",
            "Montaggio intervista chef",
            "high",
            {"riprese": -(chef + 1), "pubblicazione": 5},
            [
                (chef + 10, "alessandra", "crea", None),
                (chef + 8, "giulia", "fase", "approvazione_script"),
                (chef + 8, "alessandra", "invia", None),
                (chef + 6, "alessandra", "approva", None),
                (chef + 1, "alessandra", "fase", "girato"),
                (chef, "dario", "fase", "montaggio"),  # due the working day before: late
            ],
        ),
        (
            "ALFV",
            "Reel tutorial ricetta",
            "urgent",
            {"riprese": -3, "pubblicazione": 7},
            [
                (12, "alessandra", "crea", None),
                (10, "giulia", "fase", "approvazione_script"),
                (10, "alessandra", "invia", None),
                (8, "alessandra", "approva", None),
                (3, "alessandra", "fase", "girato"),
                (0, "dario", "fase", "montaggio"),  # Urgente: due the next working day
            ],
        ),
        (
            "ALFV",
            "Reel ricetta di Natale",
            "medium",
            {"riprese": 7, "pubblicazione": 40},
            [
                (8, "alessandra", "crea", None),
                (6, "giulia", "fase", "approvazione_script"),
                (6, "alessandra", "invia", None),
                (2, "alessandra", "approva", None),  # "Da girare", no videomaker: to assign
            ],
        ),
        (
            "ALFV",
            "Reel offerta del mese",
            "medium",
            {"riprese": 10, "pubblicazione": 20},
            [
                (4, "alessandra", "crea", None),
                (1, "giulia", "fase", "approvazione_script"),  # ready to send
            ],
        ),
        (
            "ALFS",
            "Carosello dietro le quinte",
            "medium",
            {"pubblicazione": 5},
            [
                (20, "alessandra", "crea", None),
                (18, "giulia", "fase", "approvazione_struttura"),
                (18, "alessandra", "invia", None),
                (15, "alessandra", "approva", None),
                (10, "carla", "fase", "revisione_interna"),
                (9, "giulia", "fase", "approvazione_cliente"),
                (9, "alessandra", "invia", None),
                (6, "alessandra", "approva", None),  # scheduled: back to Giulia
            ],
        ),
        (
            "ALFS",
            "Post offerta di Natale",
            "medium",
            {"pubblicazione": 35},
            [
                (12, "alessandra", "crea", None),
                (10, "giulia", "fase", "approvazione_struttura"),
                (10, "alessandra", "invia", None),
                (7, "alessandra", "approva", None),
                (0, "carla", "fase", "revisione_interna"),
            ],
        ),
        (
            "ALFS",
            "Carosello ricette d'autunno",
            "medium",
            {"pubblicazione": 21},
            [(2, "alessandra", "crea", None)],
        ),
        (
            "ALFS",
            "Post lancio biscotto al cacao",
            "medium",
            {"pubblicazione": 28},
            [(2, "alessandra", "crea", None)],
        ),
    ]


def read_people(text):
    """The rows of the table under "## Zeta3 Collaudo": {who: {"nome", "cognome", "email", "password"}}."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip().startswith(SECTION)), None)
    if start is None:
        raise CommandError(f'Nel file delle credenziali manca la sezione "{SECTION}".')
    header, people = None, {}
    for line in lines[start + 1 :]:
        if line.startswith("#"):
            break
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip().strip("`").strip() for cell in line.strip().strip("|").split("|")]
        if header is None:
            header = [cell.casefold() for cell in cells]
            continue
        if set(line.strip()) <= set("|-: "):
            continue  # the row under the header
        row = dict(zip(header, cells))
        people[row.get("chi", "").casefold()] = row
    if set(people) != set(PEOPLE):
        raise CommandError(f"Nella tabella servono esattamente queste persone (colonna Chi): {', '.join(PEOPLE)}.")
    for who, row in people.items():
        try:
            validate_email(row.get("email", ""))
        except ValidationError:
            raise CommandError(f"Email non valida per {who}.") from None
        if not row.get("nome"):
            raise CommandError(f"Manca il nome di {who}.")
    return people


def _history(issue, actor, kind, requested, current=None):
    """The line Plane writes in the history when a person does the same from the interface."""
    issue_activity(
        type=f"issue.activity.{kind}",
        requested_data=json.dumps(requested, cls=DjangoJSONEncoder),
        current_instance=json.dumps(current, cls=DjangoJSONEncoder) if current is not None else None,
        issue_id=str(issue.id),
        actor_id=str(actor.id),
        project_id=str(issue.project_id),
        epoch=int(timezone.now().timestamp()),
        notification=False,
    )


def _backdate(workspace, start, shift):
    """Everything written in the workspace since `start` moves back by `shift`: the history, the
    notices, the phases entered and the client's answers keep their order, on the planned day."""
    IssueActivity.objects.filter(workspace=workspace, created_at__gte=start).update(
        created_at=F("created_at") + shift, epoch=F("epoch") + shift.total_seconds()
    )
    rows = (
        (Issue.all_objects.filter(workspace=workspace), ("created_at", "updated_at")),
        (IssueActivity.objects.filter(workspace=workspace), ("updated_at",)),
        (Notification.objects.filter(workspace=workspace), ("created_at", "updated_at")),
        (PhaseEntry.objects.filter(issue__workspace=workspace), ("created_at", "updated_at")),
        (ClientApproval.objects.filter(issue__workspace=workspace), ("created_at", "updated_at", "decided_at")),
    )
    for queryset, fields in rows:
        for field in fields:
            queryset.filter(**{f"{field}__gte": start}).update(**{field: F(field) + shift})


class Command(BaseCommand):
    help = 'Crea lo spazio "Zeta3 Collaudo" con dati inventati per il collaudo online (mai dati veri).'

    def add_arguments(self, parser):
        parser.add_argument(
            "--persone",
            required=True,
            help='Il file locale delle credenziali, oppure "-" per leggerlo dallo standard input.',
        )
        parser.add_argument(
            "--nuovo-giro",
            action="store_true",
            help="Secondo giro: archivia lo spazio del giro prima (rinominato, senza membri) e ne crea uno nuovo.",
        )

    def handle(self, *args, **options):
        if os.environ.get("ATLANTE_AMBIENTE") != "prova":
            raise CommandError(
                "Rifiutato: questo comando gira solo con ATLANTE_AMBIENTE=prova. Non va mai usato su dati veri."
            )
        source = options["persone"]
        people = read_people(sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8"))
        instance = Instance.objects.first()
        if instance is None:
            raise CommandError("L'installazione non è ancora registrata: avvia prima il server.")
        existing = Workspace.objects.filter(slug=WORKSPACE_SLUG).first()
        if existing is not None and not options["nuovo_giro"]:
            raise CommandError(
                f"Lo spazio {WORKSPACE_SLUG} esiste già e non si rilancia durante la prova. "
                "Per un secondo giro, dopo le correzioni: --nuovo-giro."
            )

        self.today = rome_today()
        with transaction.atomic():
            archived = self._archive(existing) if existing is not None else None
            users, kept = self._people(people)
            self._instance(instance, users["rick"])
            self.workspace = self._workspace(users)
            projects = {spec[0]: self._project(spec, users) for spec in PROJECTS}
            self._clients(users, projects)
            for spec in plan(self.today):
                self._task(projects[spec[0]], spec, users)
            first = self.today.replace(day=1)
            with impersonate(None), self._on(first, REPORT_MORNING):
                create_report(projects["ALFS"], first)
            for ago in range(MORNINGS, -1, -1):
                day = self.today - timedelta(days=ago)
                with impersonate(None), self._on(day, MORNING):
                    approvals.daily(day, workspace_id=self.workspace.id)
            # The notices of the preparation are already read: during the trial only the new ones count.
            Notification.objects.filter(workspace=self.workspace, read_at__isnull=True).update(read_at=timezone.now())

        tasks = Issue.issue_objects.filter(workspace=self.workspace).count()
        if archived:
            self.stdout.write(f"Il giro prima è archiviato come {archived}.")
        for who in PEOPLE:
            state = "account esistente, password invariata" if who in kept else "account creato"
            self.stdout.write(f"{who}: {users[who].email} ({state})")
        self.stdout.write(
            self.style.SUCCESS(
                f"Creato '{WORKSPACE_NAME}' ({WORKSPACE_SLUG}): {len(PROJECTS)} progetti, {tasks} task, "
                f"date contate da oggi {self.today.isoformat()}."
            )
        )

    @contextmanager
    def _on(self, day, at):
        """The rules run as on `day` and what they write gets that day and time, as if done then."""
        start = timezone.now()
        with as_on(day):
            yield
        if day < self.today:
            _backdate(self.workspace, start, datetime.combine(day, at, tzinfo=ROME) - start)

    def _archive(self, workspace):
        number = Workspace.objects.filter(slug__startswith=f"{WORKSPACE_SLUG}-giro-").count() + 1
        workspace.slug = f"{WORKSPACE_SLUG}-giro-{number}"
        workspace.name = f"{WORKSPACE_NAME}, giro {number} (archiviato)"
        workspace.save()
        WorkspaceMember.objects.filter(workspace=workspace).update(is_active=False)
        ProjectMember.objects.filter(workspace=workspace).update(is_active=False)
        return workspace.slug

    def _people(self, people):
        users, kept = {}, set()
        for who, row in people.items():
            user = User.objects.filter(email=row["email"].lower()).first()
            if user is not None:
                kept.add(who)
            else:
                password = row.get("password", "")
                if len(password) < 12:
                    raise CommandError(f"La password di {who} deve avere almeno 12 caratteri.")
                user = self._new_user(row["email"].lower(), row["nome"], row.get("cognome", ""), who, password)
            users[who] = user
        for who, (first, last, _job) in COLLEAGUES.items():
            email = f"{who}@{COLLEAGUES_DOMAIN}"
            users[who] = User.objects.filter(email=email).first() or self._new_user(email, first, last, who, None)
        return users, kept

    def _new_user(self, email, first, last, handle, password):
        user = User(
            email=email,
            username=uuid.uuid4().hex,
            first_name=first,
            last_name=last,
            display_name=handle,
            is_active=True,
            is_email_verified=True,
            is_password_autoset=False,
            user_timezone="Europe/Rome",
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()  # an invented colleague: nobody signs in as them
        user.save()
        Profile.objects.create(
            user=user,
            is_onboarded=True,
            is_tour_completed=True,
            is_navigation_tour_completed=True,
            onboarding_step={
                "profile_complete": True,
                "workspace_create": True,
                "workspace_invite": True,
                "workspace_join": True,
            },
            language="it",
            start_of_the_week=Profile.MONDAY,
            billing_address_country="ITALY",
        )
        return user

    def _instance(self, instance, admin):
        """On a new server Rick is the administrator of the installation. Nobody signs up alone."""
        if not InstanceAdmin.objects.exists():
            InstanceAdmin.objects.create(user=admin, instance=instance, role=ADMIN)
            instance.is_setup_done = True
            instance.is_signup_screen_visited = True
            instance.save()
        InstanceConfiguration.objects.update_or_create(
            key="ENABLE_SIGNUP", defaults={"value": "0", "category": "AUTHENTICATION", "is_encrypted": False}
        )

    def _workspace(self, users):
        workspace = Workspace.objects.create(
            name=WORKSPACE_NAME,
            slug=WORKSPACE_SLUG,
            owner=users["rick"],
            timezone="Europe/Rome",
            organization_size="2-10",
        )
        for who, (role, job) in PEOPLE.items():
            WorkspaceMember.objects.create(workspace=workspace, member=users[who], role=role, company_role=job)
            Profile.objects.filter(user=users[who]).update(last_workspace_id=workspace.id)
        for who, (_first, _last, job) in COLLEAGUES.items():
            WorkspaceMember.objects.create(workspace=workspace, member=users[who], role=MEMBER, company_role=job)
        return workspace

    def _project(self, spec, users):
        identifier, name, template, roles = spec
        workspace = self.workspace
        project = Project.objects.create(
            workspace=workspace,
            name=name,
            identifier=identifier,
            description="Progetto inventato per il collaudo di Atlante.",
            network=2,
            project_lead=users["alessandra"],
            timezone="Europe/Rome",
            module_view=True,
            cycle_view=False,
            issue_views_view=True,
            page_view=True,
            intake_view=True,
        )
        ProjectIdentifier.objects.create(name=identifier, project=project, workspace=workspace)
        # The whole team is in both projects; only Rick and Alessandra are its administrators.
        for who in (*PEOPLE, *COLLEAGUES):
            role = ADMIN if who in PROJECT_ADMINS else MEMBER
            ProjectMember.objects.create(project=project, member=users[who], role=role, workspace=workspace)
        State.objects.bulk_create(
            [
                State(
                    name=state["name"],
                    color=state["color"],
                    project=project,
                    sequence=state["sequence"],
                    workspace=workspace,
                    group=state["group"],
                    default=state.get("default", False),
                    created_by=users["rick"],  # bulk_create skips save(): set it here
                )
                for state in DEFAULT_STATES
            ]
        )
        apply_template(project, template)
        for role, handles in roles.items():
            for who in handles:
                ProjectRole.objects.create(project=project, role=role, member=users[who])
        return project

    def _clients(self, users, projects):
        for name, code, color, rounds in CLIENTS:
            client = Client.objects.create(
                workspace=self.workspace,
                name=name,
                code=code,
                color=color,
                internal_contact=users["alessandra"],
                email=f"info@{code.lower()}.{COLLEAGUES_DOMAIN}",
                internal_notes="Cliente inventato per il collaudo di Atlante.",
                included_revisions=rounds,
            )
            if code == "ALF":
                for project in projects.values():
                    ProjectClient.objects.create(project=project, client=client, workspace=self.workspace)

    def _task(self, project, spec, users):
        _code, title, urgency, dates, steps = spec
        phases = {b.phase: b.state for b in PhaseBinding.objects.filter(project=project).select_related("state")}
        issue = None
        for index, (ago, who, what, phase) in enumerate(steps):
            day = self.today - timedelta(days=ago)
            at = (datetime.combine(day, FIRST_STEP) + index * STEP_GAP).time()
            actor = users[who]
            with impersonate(actor), self._on(day, at):
                if what == "crea":
                    issue = Issue.objects.create(
                        project=project,
                        workspace=self.workspace,
                        name=title,
                        description_html="<p>Task inventata per il collaudo di Atlante.</p>",
                        state=State.objects.get(project=project, default=True),
                        priority=urgency,
                    )
                    for kind, offset in dates.items():
                        TaskDate.objects.create(issue=issue, kind=kind, day=self.today + timedelta(days=offset))
                    enter_phase(issue, created=True)
                    _history(issue, actor, "created", {"name": title})
                    continue
                # Read again at every step: the step before moved its dates back.
                issue = Issue.issue_objects.get(pk=issue.pk)
                if what == "fase":
                    before = issue.state_id
                    issue.state = phases[phase]
                    issue.save()
                    _history(issue, actor, "updated", {"state_id": str(issue.state_id)}, {"state_id": str(before)})
                elif what == "invia":
                    approvals.send(issue, approvals.open_approval(issue), actor)
                elif what == "approva":
                    approvals.decide(issue, approvals.open_approval(issue), approved=True, user=actor)
        return issue
