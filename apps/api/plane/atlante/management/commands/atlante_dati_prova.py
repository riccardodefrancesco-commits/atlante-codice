# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Creates invented test data for Atlante: never real data.

Usage, inside the api container:
    python manage.py atlante_dati_prova [--lavori-extra 2000]
    python manage.py atlante_dati_prova --progetto-video   # only the Video project, on existing data

It refuses to run unless ATLANTE_AMBIENTE=prova and ATLANTE_PASSWORD_PROVA
(the shared password of the invented users) are set in apps/api/.env.
"""

import os
import random
import uuid
from datetime import timedelta

from crum import impersonate
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from plane.db.models import (
    Issue,
    IssueAssignee,
    IssueLabel,
    Label,
    Profile,
    Project,
    ProjectIdentifier,
    ProjectMember,
    State,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.atlante.models import Client, IssueClient, PhaseBinding, ProjectClient, ProjectRole, TaskDate
from plane.atlante.phases import apply_template, enter_phase, today as rome_today
from plane.db.models.state import DEFAULT_STATES
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration

WORKSPACE_SLUG = "zeta3-prova"
WORKSPACE_NAME = "Zeta3 Prova"
EMAIL_DOMAIN = "esempio.it"

ADMIN, MEMBER, GUEST = 20, 15, 5

# (first name, last name, email user, workspace role, job)
PEOPLE = [
    ("Admin", "Prova", "admin", ADMIN, "Amministratore"),
    ("Anna", "Prova", "anna", ADMIN, "Account e project manager"),
    ("Bruno", "Prova", "bruno", MEMBER, "Social media manager"),
    ("Carla", "Prova", "carla", MEMBER, "Grafica"),
    ("Dario", "Prova", "dario", MEMBER, "Videomaker"),
    ("Elena", "Prova", "elena", MEMBER, "Editor video"),
    ("Fabio", "Ospite", "fabio", GUEST, "Cliente finto"),
]

# (identifier, name, description, members by email user, labels, title templates)
SOCIAL_TITLES = [
    "Reel {tema}",
    "Carosello {tema}",
    "Post {tema}",
    "Copertina reel {tema}",
    "Script reel {tema}",
    "Stories {tema}",
]
PROJECTS = [
    (
        "ALFA",
        "Alfa Biscotti: social",
        "Gestione dei social di Alfa Biscotti (cliente inventato).",
        ["anna", "bruno", "carla", "dario", "elena", "fabio"],
        ["Instagram", "TikTok", "Facebook"],
        SOCIAL_TITLES,
    ),
    (
        "BETA",
        "Beta Moda: social",
        "Gestione dei social di Beta Moda (cliente inventato).",
        ["anna", "bruno", "carla", "dario", "elena"],
        ["Instagram", "LinkedIn", "Newsletter"],
        SOCIAL_TITLES,
    ),
    (
        "GAMMA",
        "Gamma Palestre: sito",
        "Nuovo sito di Gamma Palestre (cliente inventato).",
        ["anna", "carla"],
        ["Design", "Testi", "Sviluppo"],
        [
            "Wireframe {tema}",
            "Testi pagina {tema}",
            "Design pagina {tema}",
            "Sviluppo pagina {tema}",
            "Controllo bug {tema}",
        ],
    ),
    (
        "DELTA",
        "Delta Vini: brand",
        "Brand completo di Delta Vini (cliente inventato).",
        ["anna", "carla"],
        ["Logo", "Immagine coordinata", "Brand manual"],
        [
            "Moodboard {tema}",
            "Proposta logo {tema}",
            "Palette colori {tema}",
            "Biglietti da visita {tema}",
            "Brand manual: capitolo {tema}",
        ],
    ),
    (
        "VIDEO",
        "Produzione video (prova)",
        "Tutti i video da girare e montare, di più clienti inventati.",
        ["anna", "bruno", "dario", "elena"],
        ["Riprese", "Montaggio", "Copertina"],
        [
            "Riprese {tema}",
            "Montaggio reel {tema}",
            "Montaggio video lungo {tema}",
            "Color correction {tema}",
            "Sottotitoli {tema}",
        ],
    ),
    (
        "INT",
        "Interno (prova)",
        "Lavori interni dell'agenzia, inventati.",
        ["anna", "bruno", "carla", "dario", "elena"],
        ["Amministrazione", "Formazione", "Strumenti"],
        [
            "Aggiornare {tema}",
            "Preparare {tema}",
            "Riunione su {tema}",
            "Controllare {tema}",
        ],
    ),
]

THEMES = [
    "novità di stagione",
    "dietro le quinte",
    "evento di novembre",
    "offerta del mese",
    "presentazione team",
    "tutorial",
    "domande frequenti",
    "home",
    "chi siamo",
    "contatti",
    "listino",
    "calendario editoriale",
    "Natale",
    "Black Friday",
    "intervista",
]

# (name, code, color, project identifier or None, internal contact)
CLIENTS = [
    ("Alfa Biscotti", "ALF", "#E5484D", "ALFA", "bruno"),
    ("Beta Moda", "BET", "#8E4EC6", "BETA", "bruno"),
    ("Gamma Palestre", "GAM", "#46A758", "GAMMA", "anna"),
    ("Delta Vini", "DEL", "#F59E0B", "DELTA", "anna"),
]
# Projects without a client: their work items get their own client.
PROJECTS_WITHOUT_CLIENT_WITH_OWN = ["VIDEO"]

PRIORITIES = ["urgent", "high", "medium", "low", "none"]
ISSUES_PER_PROJECT = 25

# A project with the Video template (assaggio B): roles, and tasks moved through their phases.
VIDEO_PROJECT = (
    "ALFV",
    "Alfa Biscotti: video",
    "Video e reel di Alfa Biscotti (cliente inventato), con il modello Video.",
    ["anna", "bruno", "carla", "dario", "elena", "fabio"],
)
VIDEO_ROLES = {
    "account": ["anna"],
    "social_media_manager": ["bruno"],
    "lead_videomaker": ["dario"],
    "videomaker": ["dario"],
    "editor": ["elena"],
    "revisore_interno": ["bruno", "admin"],
    "project_manager": ["anna"],
    "grafico": ["carla"],
}
VIDEO_PATH = ["script", "approvazione_script", "da_girare", "girato", "montaggio", "revisione_interna"]
# (title, priority, how many phases it went through, shooting day from today)
VIDEO_TASKS = [
    ("Reel novità di stagione", "medium", 1, 9),
    ("Reel dietro le quinte", "high", 2, 6),
    ("Reel offerta del mese", "high", 3, 2),
    ("Video intervista al fondatore", "urgent", 4, -1),
    ("Reel tutorial ricetta", "medium", 5, -3),
    ("Reel evento di novembre", "low", 6, -5),
]


class Command(BaseCommand):
    help = "Crea dati inventati per provare Atlante (mai dati veri)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--lavori-extra",
            type=int,
            default=0,
            help="Lavori inventati in più, divisi tra i progetti (per la prova di velocità).",
        )
        parser.add_argument(
            "--progetto-video",
            action="store_true",
            help="Solo il progetto con il modello Video, sui dati di prova già creati.",
        )

    def handle(self, *args, **options):
        if os.environ.get("ATLANTE_AMBIENTE") != "prova":
            raise CommandError(
                "Rifiutato: questo comando gira solo con ATLANTE_AMBIENTE=prova. Non va mai usato su dati veri."
            )
        password = os.environ.get("ATLANTE_PASSWORD_PROVA", "")
        if len(password) < 12:
            raise CommandError("Manca ATLANTE_PASSWORD_PROVA (almeno 12 caratteri) in apps/api/.env.")

        instance = Instance.objects.first()
        if instance is None:
            raise CommandError("L'installazione non è ancora registrata: avvia prima il server.")

        if Workspace.objects.filter(slug=WORKSPACE_SLUG).exists():
            if options["progetto_video"]:
                workspace = Workspace.objects.get(slug=WORKSPACE_SLUG)
                if Project.objects.filter(workspace=workspace, identifier=VIDEO_PROJECT[0]).exists():
                    raise CommandError("Il progetto con il modello Video esiste già.")
                with transaction.atomic(), impersonate(workspace.owner):
                    count = self._create_video_project(workspace)
                self.stdout.write(self.style.SUCCESS(f"Creato il progetto con il modello Video e {count} task."))
                return
            if options["lavori_extra"]:
                workspace = Workspace.objects.get(slug=WORKSPACE_SLUG)
                with transaction.atomic(), impersonate(workspace.owner):
                    created = self._extra_issues(workspace, options["lavori_extra"])
                self.stdout.write(self.style.SUCCESS(f"Aggiunti {created} lavori inventati."))
                return
            workspace = Workspace.objects.get(slug=WORKSPACE_SLUG)
            if not Client.objects.filter(workspace=workspace).exists():
                # Data created before clients existed (piece 1): add only the clients.
                with transaction.atomic(), impersonate(workspace.owner):
                    count = self._create_clients(workspace)
                self.stdout.write(self.style.SUCCESS(f"Aggiunti {count} clienti inventati."))
                return
            raise CommandError(f"Lo spazio {WORKSPACE_SLUG} esiste già: i dati di prova sono già stati creati.")

        rng = random.Random(2026)
        with transaction.atomic():
            users = self._create_users(password)
            # Plane fills "created by" from the current user: act as the invented admin.
            with impersonate(users["admin"]):
                workspace, issue_count = self._create_everything(users, instance, rng, options)

        self.stdout.write(
            self.style.SUCCESS(
                f"Creati: spazio '{WORKSPACE_NAME}', {len(users)} persone, {len(PROJECTS)} progetti, "
                f"{issue_count} lavori. Accesso con le email @{EMAIL_DOMAIN} e la password di prova."
            )
        )

    def _create_everything(self, users, instance, rng, options):
        workspace = self._create_workspace(users)
        InstanceAdmin.objects.get_or_create(user=users["admin"], instance=instance, role=ADMIN)
        # Same flags Plane sets when the first admin completes the setup screens.
        instance.is_setup_done = True
        instance.is_signup_screen_visited = True
        instance.save()
        # Nobody signs up alone: people join only by invitation (zeta3-progetti#10).
        InstanceConfiguration.objects.update_or_create(
            key="ENABLE_SIGNUP", defaults={"value": "0", "category": "AUTHENTICATION", "is_encrypted": False}
        )
        for user in users.values():
            Profile.objects.filter(user=user).update(last_workspace_id=workspace.id)
        issue_count = 0
        for spec in PROJECTS:
            issue_count += self._create_project(workspace, users, spec, rng)
        self._create_clients(workspace)
        issue_count += self._create_video_project(workspace)
        if options["lavori_extra"]:
            issue_count += self._extra_issues(workspace, options["lavori_extra"])
        return workspace, issue_count

    def _create_clients(self, workspace):
        members = {m.member.email.split("@")[0]: m.member for m in WorkspaceMember.objects.filter(workspace=workspace)}
        projects = {p.identifier: p for p in Project.objects.filter(workspace=workspace)}
        clients = []
        for name, code, color, identifier, contact in CLIENTS:
            client = Client.objects.create(
                workspace=workspace,
                name=name,
                code=code,
                color=color,
                internal_contact=members.get(contact),
                email=f"info@{code.lower()}.{EMAIL_DOMAIN}",
                internal_notes="Cliente inventato per la prova di Atlante.",
            )
            if identifier in projects:
                ProjectClient.objects.create(project=projects[identifier], client=client, workspace=workspace)
            clients.append(client)
        # In projects without a client, every work item belongs to one of the clients.
        for identifier in PROJECTS_WITHOUT_CLIENT_WITH_OWN:
            project = projects.get(identifier)
            if project is None:
                continue
            for i, issue in enumerate(Issue.issue_objects.filter(project=project).order_by("sequence_id")):
                IssueClient.objects.create(
                    issue=issue, client=clients[i % len(clients)], project=project, workspace=workspace
                )
        return len(clients)

    def _create_users(self, password):
        users = {}
        for first, last, handle, _role, _job in PEOPLE:
            user = User(
                email=f"{handle}@{EMAIL_DOMAIN}",
                username=uuid.uuid4().hex,
                first_name=first,
                last_name=last,
                display_name=handle,
                is_active=True,
                is_email_verified=True,
                is_password_autoset=False,
                user_timezone="Europe/Rome",
            )
            user.set_password(password)
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
            users[handle] = user
        return users

    def _create_workspace(self, users):
        workspace = Workspace.objects.create(
            name=WORKSPACE_NAME,
            slug=WORKSPACE_SLUG,
            owner=users["admin"],
            timezone="Europe/Rome",
            organization_size="2-10",
        )
        for _first, _last, handle, role, job in PEOPLE:
            WorkspaceMember.objects.create(
                workspace=workspace,
                member=users[handle],
                role=role,
                company_role=job,
            )
        return workspace

    def _new_project(self, workspace, users, identifier, name, description, member_handles):
        admin = users["admin"]
        project = Project.objects.create(
            workspace=workspace,
            name=name,
            identifier=identifier,
            description=description,
            network=2,
            project_lead=users["anna"],
            timezone="Europe/Rome",
            module_view=True,
            cycle_view=False,
            issue_views_view=True,
            page_view=True,
            intake_view=True,
        )
        ProjectIdentifier.objects.create(name=identifier, project=project, workspace=workspace)

        ProjectMember.objects.create(project=project, member=admin, role=ADMIN, workspace=workspace)
        roles = {handle: role for _f, _l, handle, role, _j in PEOPLE}
        for handle in member_handles:
            ProjectMember.objects.create(project=project, member=users[handle], role=roles[handle], workspace=workspace)

        states = State.objects.bulk_create(
            [
                State(
                    name=state["name"],
                    color=state["color"],
                    project=project,
                    sequence=state["sequence"],
                    workspace=workspace,
                    group=state["group"],
                    default=state.get("default", False),
                    created_by=admin,  # bulk_create skips save(): set it here
                )
                for state in DEFAULT_STATES
            ]
        )
        return project, states

    def _create_project(self, workspace, users, spec, rng):
        identifier, name, description, member_handles, label_names, titles = spec
        admin = users["admin"]
        roles = {handle: role for _f, _l, handle, role, _j in PEOPLE}
        project, states = self._new_project(workspace, users, identifier, name, description, member_handles)
        visible_states = [s for s in states if s.group != "triage"]

        labels = [
            Label.objects.create(
                name=label_name,
                project=project,
                workspace=workspace,
                color=rng.choice(["#E5484D", "#3E63DD", "#46A758", "#F59E0B", "#8E4EC6"]),
            )
            for label_name in label_names
        ]

        workers = [users[h] for h in member_handles if roles[h] != GUEST]
        today = timezone.now().date()
        created = []
        for _ in range(ISSUES_PER_PROJECT):
            created.append(
                self._create_issue(project, workspace, admin, visible_states, labels, workers, titles, today, rng)
            )
        # A few sub-items, to test parents and children.
        for parent in created[:4]:
            for step in ("bozza", "revisione"):
                child = self._create_issue(
                    project, workspace, admin, visible_states, labels, workers, titles, today, rng
                )
                child.name = f"{parent.name}: {step}"
                child.parent = parent
                child.save()
        return ISSUES_PER_PROJECT + 8

    def _create_video_project(self, workspace):
        users = {
            m.member.email.split("@")[0]: m.member
            for m in WorkspaceMember.objects.filter(workspace=workspace).select_related("member")
        }
        identifier, name, description, member_handles = VIDEO_PROJECT
        project, _ = self._new_project(workspace, users, identifier, name, description, member_handles)
        apply_template(project, "video")
        for role, handles in VIDEO_ROLES.items():
            for handle in handles:
                ProjectRole.objects.create(project=project, role=role, member=users[handle])
        client = Client.objects.filter(workspace=workspace, code="ALF").first()
        if client is not None:
            ProjectClient.objects.create(project=project, client=client, workspace=workspace)
        phases = {b.phase: b.state for b in PhaseBinding.objects.filter(project=project).select_related("state")}
        today = rome_today()
        for title, priority, steps, shooting in VIDEO_TASKS:
            issue = Issue.objects.create(
                project=project,
                workspace=workspace,
                name=title,
                description_html="<p>Video inventato per la prova del modello Video.</p>",
                state=phases[VIDEO_PATH[0]],
                priority=priority,
            )
            TaskDate.objects.create(issue=issue, kind="riprese", day=today + timedelta(days=shooting))
            TaskDate.objects.create(issue=issue, kind="pubblicazione", day=today + timedelta(days=shooting + 12))
            enter_phase(issue, created=True)
            # Every move runs the phase rule, as when someone drags the card.
            for phase in VIDEO_PATH[1:steps]:
                issue.state = phases[phase]
                issue.save()
        return len(VIDEO_TASKS)

    def _create_issue(self, project, workspace, creator, states, labels, workers, titles, today, rng):
        start = today + timedelta(days=rng.randint(-20, 10))
        issue = Issue.objects.create(
            project=project,
            workspace=workspace,
            name=rng.choice(titles).format(tema=rng.choice(THEMES)),
            description_html="<p>Lavoro inventato per la prova di Atlante.</p>",
            state=rng.choice(states),
            priority=rng.choice(PRIORITIES),
            start_date=start,
            target_date=start + timedelta(days=rng.randint(1, 14)),
        )
        for assignee in rng.sample(workers, k=min(len(workers), rng.choice([1, 1, 2]))):
            IssueAssignee.objects.create(issue=issue, assignee=assignee, project=project, workspace=workspace)
        if labels and rng.random() < 0.7:
            IssueLabel.objects.create(issue=issue, label=rng.choice(labels), project=project, workspace=workspace)
        return issue

    def _extra_issues(self, workspace, count):
        rng = random.Random(count)
        admin = workspace.owner
        today = timezone.now().date()
        projects = list(Project.objects.filter(workspace=workspace))
        specs = {spec[0]: spec for spec in PROJECTS}
        for i in range(count):
            project = projects[i % len(projects)]
            spec = specs.get(project.identifier)
            titles = spec[5] if spec else SOCIAL_TITLES
            states = list(State.objects.filter(project=project))
            labels = list(Label.objects.filter(project=project))
            workers = [
                m.member
                for m in ProjectMember.objects.filter(project=project, is_active=True).select_related("member")
                if m.role != GUEST
            ]
            self._create_issue(project, workspace, admin, states, labels, workers, titles, today, rng)
        return count
