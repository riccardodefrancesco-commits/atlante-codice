# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Checks on "Zeta3 Collaudo" every row of "Cosa deve succedere" (zeta3-progetti, docs/collaudo-0.3.md,
section 3): it does what the people do from the interface, through the same API and in the same order,
first together, then Alessandra, Virginia and Giulia alone, and compares the result with the document.

Everything happens inside a transaction that is always undone: the data stay as they were prepared and
nobody gets a notice. The background jobs of Plane (history, notices by email) are not started at all.

Usage, inside the api container, after atlante_dati_collaudo and before the people sign in:
    python manage.py atlante_verifica_collaudo
One line per row; a row that is not as written says what was different, and the command fails.
"""

from datetime import timedelta
from unittest import mock

from celery.app.task import Task
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient

from plane.atlante.models import Client, PhaseBinding, TaskDate
from plane.atlante.monthly_reports import REPORT_SECTIONS
from plane.atlante.phases import ROME, today
from plane.atlante.working_days import add_working_days
from plane.db.models import Issue, IssueActivity, IssueAssignee, Notification, State, Workspace, WorkspaceMember

from .atlante_dati_collaudo import WORKSPACE_SLUG

NEW_REEL = "Reel novità di novembre"
TOO_LOUD = "La musica è troppo alta"


class _Undo(Exception):
    """Raised at the end: the transaction is undone."""


class Person:
    """Someone signed in to the interface: the same API calls, as them."""

    def __init__(self, user, host):
        self.user = user
        self.client = APIClient(HTTP_HOST=host)
        self.client.force_authenticate(user=user)

    def call(self, method, url, data=None):
        return getattr(self.client, method)(url, data, format="json", secure=True)


class Command(BaseCommand):
    help = 'Controlla su "Zeta3 Collaudo" ogni riga di "Cosa deve succedere", senza lasciare tracce.'

    def handle(self, *args, **options):
        self.workspace = Workspace.objects.filter(slug=WORKSPACE_SLUG).first()
        if self.workspace is None:
            raise CommandError(f"Manca lo spazio {WORKSPACE_SLUG}: prima atlante_dati_collaudo.")
        self.rows = []
        try:
            # Nothing leaves this process: no history job, no email, no message to the worker.
            with transaction.atomic(), mock.patch.object(Task, "delay"), mock.patch.object(Task, "apply_async"):
                self._prepare()
                self._together()
                self._alessandra()
                self._virginia()
                self._giulia()
                raise _Undo
        except _Undo:
            pass
        failed = 0
        for label, problems, notes in self.rows:
            mark = "OK " if not problems else "NO "
            self.stdout.write(f"{mark} {label}" + "".join(f"\n      {note}" for note in notes))
            for problem in problems:
                self.stdout.write(self.style.ERROR(f"      diverso: {problem}"))
            failed += bool(problems)
        if failed:
            raise CommandError(f"{failed} righe su {len(self.rows)} non sono come scritto nel documento.")
        self.stdout.write(
            self.style.SUCCESS(f"Tutte le {len(self.rows)} righe sono come scritto. Nessun dato cambiato.")
        )

    # Reading what happened

    def _prepare(self):
        host = next((h.lstrip(".") for h in settings.ALLOWED_HOSTS if h not in ("*", "")), "localhost")
        self.people = {
            row.member.display_name: Person(row.member, host)
            for row in WorkspaceMember.objects.filter(workspace=self.workspace, is_active=True).select_related("member")
        }
        self.day = today()
        # The day the data were prepared: the dates of section 2 count from it.
        self.prepared = timezone.localtime(self.workspace.created_at, ROME).date()
        self.plane = f"/api/workspaces/{WORKSPACE_SLUG}"
        self.atlante = f"/api/atlante/workspaces/{WORKSPACE_SLUG}"
        self.since = timezone.now()

    def _row(self, label):
        self.rows.append((label, [], []))

    def _expect(self, condition, what):
        if not condition:
            self.rows[-1][1].append(what)
        return condition

    def _note(self, text):
        self.rows[-1][2].append(text)

    def _task(self, name, project="ALFV"):
        return Issue.issue_objects.get(workspace=self.workspace, project__identifier=project, name=name)

    def _doers(self, issue):
        return set(IssueAssignee.objects.filter(issue=issue).values_list("assignee__display_name", flat=True))

    def _phase(self, issue):
        return Issue.issue_objects.get(pk=issue.pk).state.name

    def _notified(self, who, issue):
        return Notification.objects.filter(
            receiver=self.people[who].user, entity_identifier=issue.id, created_at__gte=self.since
        ).exists()

    def _url(self, issue, tail=""):
        return f"{self.plane}/projects/{issue.project_id}/issues/{issue.id}/{tail}"

    def _atlante_url(self, issue, tail):
        return f"{self.atlante}/projects/{issue.project_id}/issues/{issue.id}/{tail}"

    def _ok(self, response, expected, what):
        return self._expect(
            response.status_code == expected, f"{what}: risposta {response.status_code} {response.content[:200]!r}"
        )

    # Doing what the people do

    def _move(self, who, issue, phase):
        state = PhaseBinding.objects.get(project_id=issue.project_id, phase=phase).state
        response = self.people[who].call("patch", self._url(issue), {"state_id": str(state.id)})
        self._ok(response, 204, f"{who} sposta in {state.name}")
        return Issue.issue_objects.get(pk=issue.pk)

    def _assign(self, who, issue, person):
        response = self.people[who].call(
            "patch", self._url(issue), {"assignee_ids": [str(self.people[person].user.id)]}
        )
        self._ok(response, 204, f"{who} assegna a {person}")
        return Issue.issue_objects.get(pk=issue.pk)

    def _answer(self, who, issue, esito, **extra):
        response = self.people[who].call("post", self._atlante_url(issue, "approvazione/"), {"esito": esito, **extra})
        self._ok(response, 200, f"{who}: {esito}")
        return Issue.issue_objects.get(pk=issue.pk)

    def _box(self, who, issue):
        response = self.people[who].call("get", self._atlante_url(issue, "approvazione/"))
        return (response.data or {}).get("approval") or {}

    def _choices(self, who, issue):
        response = self.people[who].call("get", self._atlante_url(issue, "scelte/"))
        self._ok(response, 200, f"{who} apre la task")
        return response.data or {}

    def _home(self, who):
        response = self.people[who].call("get", f"{self.atlante}/da-assegnare/")
        self._ok(response, 200, f"Home di {who}")
        return response.data or {}

    # Section 3, first part: together

    def _together(self):
        video = self._task("Reel offerta del mese").project
        script = State.objects.get(project=video, default=True)

        self._row(f'Prima parte 1: Alessandra crea "{NEW_REEL}", urgenza Standard')
        response = self.people["alessandra"].call(
            "post",
            f"{self.plane}/projects/{video.id}/issues/",
            {"name": NEW_REEL, "priority": "medium", "state_id": str(script.id)},
        )
        if not self._ok(response, 201, "creazione"):
            return
        reel = Issue.issue_objects.get(pk=response.data["id"])
        self._expect(self._phase(reel) == "Script", f"fase {self._phase(reel)}")
        self._expect(self._doers(reel) == {"giulia"}, f"esecutore {self._doers(reel)}")
        self._expect(self._notified("giulia", reel), "Giulia senza avviso")
        cover = Issue.issue_objects.filter(parent=reel).first()
        if self._expect(cover is not None, "nessuna copertina"):
            self._expect(self._doers(cover) == {"carla"}, f"copertina a {self._doers(cover)}")
            self._expect(
                cover.target_date == reel.target_date and cover.target_date is not None,
                f"consegna copertina {cover.target_date}, video {reel.target_date}",
            )

        self._row("Prima parte 2: Giulia scrive lo script e manda avanti")
        reel = self._move("giulia", reel, "approvazione_script")
        self._expect(self._doers(reel) == {"alessandra"}, f"esecutore {self._doers(reel)}")
        self._expect(self._notified("alessandra", reel), "Alessandra senza avviso")
        self._expect(self._box("alessandra", reel).get("status") == "da_inviare", "riquadro non da inviare")
        waiting = {row["id"]: row for row in self._home("alessandra").get("approvals", [])}
        self._expect(
            waiting.get(str(reel.id), {}).get("ready") is True, "non è nella Home tra le approvazioni, da inviare"
        )

        self._row("Prima parte 3: Alessandra, inviato al cliente, poi approvato")
        reel = self._answer("alessandra", reel, "inviata")
        reel = self._answer("alessandra", reel, "approvata")
        self._expect(self._phase(reel) == "Da girare", f"fase {self._phase(reel)}")
        self._expect(self._choices("alessandra", reel).get("to_assign") is True, "non è da assegnare")
        to_assign = {row["id"] for row in self._home("alessandra").get("to_assign", [])}
        self._expect(str(reel.id) in to_assign, "non è nella Home di Alessandra tra le task da assegnare")

        self._row("Prima parte 4: Alessandra dà la task a Dario e la porta a In montaggio")
        reel = self._assign("alessandra", reel, "dario")
        self._expect(self._doers(reel) == {"dario"}, f"esecutore {self._doers(reel)}")
        reel = self._move("alessandra", reel, "girato")
        self._expect(self._doers(reel) == {"dario"}, f"in Girato esecutore {self._doers(reel)}")
        reel = self._move("alessandra", reel, "montaggio")
        self._expect(self._doers(reel) == {"virginia"}, f"in montaggio esecutore {self._doers(reel)}")
        self._expect(self._notified("virginia", reel), "Virginia senza avviso")
        due = add_working_days(self.day, 7)
        self._expect(reel.target_date == due, f"consegna {reel.target_date}, attesa {due}")

        self._row("Prima parte 5: Virginia, link nei commenti, poi revisione")
        response = self.people["virginia"].call(
            "post", self._url(reel, "comments/"), {"comment_html": "<p>Il video: https://esempio.it/video</p>"}
        )
        self._ok(response, 201, "commento")
        reel = self._move("virginia", reel, "revisione_interna")
        self._expect(self._doers(reel) == {"giulia"}, f"esecutore {self._doers(reel)}")
        self._expect(self._notified("giulia", reel), "Giulia senza avviso")
        due = add_working_days(self.day, 2)
        self._expect(reel.target_date == due, f"consegna {reel.target_date}, attesa {due}")
        order = [b.phase for b in PhaseBinding.objects.filter(project=video).order_by("state__sequence")]
        after = order[order.index("montaggio") + 1]
        self._expect(after == "grafica_copertina", f"dopo In montaggio viene {after}")
        self._note('Nell\'elenco delle fasi, dopo "In montaggio" viene "Copertina in grafica": da osservare.')

        self._row("Prima parte 6: Giulia manda al cliente")
        reel = self._move("giulia", reel, "approvazione_cliente")
        self._expect(self._doers(reel) == {"alessandra"}, f"esecutore {self._doers(reel)}")
        self._expect(self._box("alessandra", reel).get("status") == "da_inviare", "riquadro non da inviare")

        self._row("Prima parte 7: Alessandra, inviato, poi la musica è troppo alta")
        reel = self._answer("alessandra", reel, "inviata")
        reel = self._answer("alessandra", reel, "modifiche", nota=TOO_LOUD, conta=True)
        self._expect(self._phase(reel) == "In montaggio", f"fase {self._phase(reel)}")
        self._expect(self._doers(reel) == {"virginia"}, f"esecutore {self._doers(reel)}")
        self._expect(reel.priority == "medium", f"urgenza {reel.priority}")
        box = self._box("virginia", reel)
        self._expect(
            (box.get("status"), box.get("used"), box.get("included"), box.get("visible")) == ("modifiche", 1, 2, True),
            f"riquadro {box.get('status')}, giri usati {box.get('used')} di {box.get('included')}",
        )
        self._expect(
            IssueActivity.objects.filter(issue=reel, comment__contains="giro di revisione 2 di 2 inclusi").exists(),
            'nello storico manca "Comincia il giro di revisione 2 di 2 inclusi"',
        )

        self._row("Prima parte 8: il secondo giro, fino all'approvazione")
        reel = self._move("virginia", reel, "revisione_interna")
        reel = self._move("giulia", reel, "approvazione_cliente")
        reel = self._answer("alessandra", reel, "inviata")
        box = self._box("alessandra", reel)
        self._expect(
            (box.get("round"), box.get("included")) == (2, 2),
            f"giro {box.get('round')} di {box.get('included')}: il riquadro non dice che i giri inclusi sono finiti",
        )
        reel = self._answer("alessandra", reel, "approvata")
        self._expect(self._phase(reel) == "Schedulato o pubblicato", f"fase {self._phase(reel)}")
        self._expect(self._doers(reel) == {"giulia"}, f"esecutore {self._doers(reel)}")

    # Section 3, second part: Alessandra

    def _alessandra(self):
        offer, interview = self._task("Reel offerta del mese"), self._task("Video intervista al fondatore")
        behind, christmas = self._task("Reel dietro le quinte"), self._task("Reel ricetta di Natale")

        self._row("Alessandra 1: dalla Home, i lavori che aspettano il cliente")
        home = self._home("alessandra")
        waiting = {row["name"]: row for row in home.get("approvals", [])}
        self._expect(waiting.get(offer.name, {}).get("ready") is True, f"{offer.name} non è da inviare")
        self._expect(waiting.get(interview.name, {}).get("to_confirm") is True, f"{interview.name} non è da confermare")
        left = 12 - (self.day - self.prepared).days
        found = waiting.get(behind.name, {}).get("days_left")
        self._expect(found == left, f"{behind.name}: restano {found} giorni, attesi {left}")
        self._note(f"In attesa del cliente: {', '.join(waiting) or 'nessuna'}.")

        self._row('Alessandra 2: "Reel offerta del mese" inviato, fino a quando?')
        offer = self._answer("alessandra", offer, "inviata")
        box = self._box("alessandra", offer)
        last = (self.day + timedelta(days=15)).isoformat()
        self._expect(box.get("due_on") == last, f"fino al {box.get('due_on')}, atteso {last}")

        self._row('Alessandra 3: il cliente non ha mai risposto sul "Video intervista al fondatore"')
        interview = self._answer("alessandra", interview, "silenzio_assenso")
        self._expect(self._phase(interview) == "Schedulato o pubblicato", f"fase {self._phase(interview)}")
        self._expect(self._doers(interview) == {"giulia"}, f"esecutore {self._doers(interview)}")
        self._expect(self._notified("giulia", interview), "Giulia senza avviso")

        self._row('Alessandra 4: sul "Reel dietro le quinte" la musica è troppo alta')
        behind = self._answer("alessandra", behind, "modifiche", nota=TOO_LOUD, conta=True)
        self._expect(self._phase(behind) == "In montaggio", f"fase {self._phase(behind)}")
        self._expect(self._doers(behind) == {"virginia"}, f"esecutore {self._doers(behind)}")
        self._expect(self._notified("virginia", behind), "Virginia senza avviso")
        box = self._box("alessandra", behind)
        self._expect((box.get("used"), box.get("included")) == (1, 2), "non comincia il giro 2 di 2")

        self._row("Alessandra 5: la task che nessuno gira, a Dario")
        to_assign = [row["name"] for row in self._home("alessandra").get("to_assign", [])]
        self._expect(christmas.name in to_assign, f"nella Home da assegnare: {to_assign}")
        christmas = self._assign("alessandra", christmas, "dario")
        self._expect(self._doers(christmas) == {"dario"}, f"esecutore {self._doers(christmas)}")
        self._expect(self._choices("alessandra", christmas).get("to_assign") is False, '"Da assegnare" resta')
        shooting = TaskDate.objects.get(issue=christmas, kind="riprese").day
        self._expect(christmas.target_date == shooting, f"consegna {christmas.target_date}, riprese {shooting}")

        self._row("Alessandra 6: progetto video di Zeta Gelati, collegato al cliente, Virginia ai montaggi")
        alessandra = self.people["alessandra"]
        response = alessandra.call(
            "post", f"{self.plane}/projects/", {"name": "Zeta Gelati · Video", "identifier": "ZETV", "network": 2}
        )
        if self._ok(response, 201, "nuovo progetto"):
            project_id = response.data["id"]
            base = f"{self.atlante}/projects/{project_id}"
            self._ok(alessandra.call("post", f"{base}/modello/", {"template": "video"}), 200, "modello Video e reel")
            zeta = Client.objects.get(workspace=self.workspace, name="Zeta Gelati")
            self._ok(
                alessandra.call("put", f"{base}/client/", {"client_id": str(zeta.id)}), 200, "collegamento al cliente"
            )
            virginia = str(self.people["virginia"].user.id)
            before = alessandra.call("put", f"{base}/ruoli/", {"role": "editor", "member_ids": [virginia]})
            if before.status_code == 400:
                self._note("Virginia va prima aggiunta ai membri del progetto: senza, il ruolo Editor non la accetta.")
            members = {"members": [{"member_id": virginia, "role": 15}]}
            self._ok(
                alessandra.call("post", f"{self.plane}/projects/{project_id}/members/", members),
                201,
                "Virginia nel progetto",
            )
            response = alessandra.call("put", f"{base}/ruoli/", {"role": "editor", "member_ids": [virginia]})
            if self._ok(response, 200, "Virginia nel ruolo Editor"):
                editors = next(role["member_ids"] for role in response.data["roles"] if role["key"] == "editor")
                self._expect(editors == [virginia], f"editor {editors}")

        self._row('Alessandra 7: "Girato" diventa "Riprese fatte"')
        filmed = PhaseBinding.objects.get(project_id=christmas.project_id, phase="girato").state
        response = alessandra.call(
            "patch", f"{self.plane}/projects/{christmas.project_id}/states/{filmed.id}/", {"name": "Riprese fatte"}
        )
        self._ok(response, 200, "nuovo nome")
        christmas = self._move("alessandra", christmas, "girato")
        self._expect(self._phase(christmas) == "Riprese fatte", f"fase {self._phase(christmas)}")
        self._expect(self._doers(christmas) == {"dario"}, f"esecutore {self._doers(christmas)}: non il lead videomaker")

    # Section 3, second part: Virginia

    def _virginia(self):
        chef, tutorial = self._task("Montaggio intervista chef"), self._task("Reel tutorial ricetta")
        virginia = self.people["virginia"].user

        self._row("Virginia 1: le tue task e quelle in ritardo")
        mine = Issue.issue_objects.filter(
            workspace=self.workspace, issue_assignee__assignee=virginia, issue_assignee__deleted_at__isnull=True
        ).exclude(state__group__in=("completed", "cancelled"))
        self._expect(chef in mine, f"{chef.name} non è sua")
        self._expect(
            chef.target_date is not None and chef.target_date < self.day, f"{chef.name}: consegna {chef.target_date}"
        )
        self._note(f"Sue: {', '.join(sorted(mine.values_list('name', flat=True)))}.")

        self._row('Virginia 2: "Reel tutorial ricetta", consegna, urgenza, chi lo rivede')
        choices = self._choices("virginia", tutorial)
        reviewers = next((role for role in choices.get("roles", []) if role["key"] == "revisore_interno"), {})
        giulia = str(self.people["giulia"].user.id)
        self._expect(reviewers.get("member_ids") == [], f"revisori scelti sulla task {reviewers.get('member_ids')}")
        self._expect(reviewers.get("project_member_ids") == [giulia], "il revisore del progetto non è Giulia")
        self._expect(tutorial.priority == "urgent", f"urgenza {tutorial.priority}")
        due = add_working_days(self.prepared, 1)
        self._expect(tutorial.target_date == due, f"consegna {tutorial.target_date}, attesa {due}")

        self._row("Virginia 3: tutti i video in montaggio")
        editing = set(
            Issue.issue_objects.filter(
                project_id=tutorial.project_id, state__atlante_phase__phase="montaggio"
            ).values_list("name", flat=True)
        )
        expected = {chef.name, tutorial.name, "Reel dietro le quinte"}
        self._expect(expected <= editing, f"in montaggio: {sorted(editing)}")

        self._row("Virginia 4: i montaggi li fa Dario, prova a cambiarlo")
        url = f"{self.atlante}/projects/{tutorial.project_id}"
        self._ok(self.people["virginia"].call("get", f"{url}/modello/"), 200, "vede i ruoli")
        dario = str(self.people["dario"].user.id)
        response = self.people["virginia"].call("put", f"{url}/ruoli/", {"role": "editor", "member_ids": [dario]})
        self._ok(response, 403, "cambia il ruolo")

    # Section 3, second part: Giulia

    def _giulia(self):
        autumn = self._task("Carosello ricette d'autunno", "ALFS")
        cocoa, christmas = (
            self._task("Post lancio biscotto al cacao", "ALFS"),
            self._task("Post offerta di Natale", "ALFS"),
        )
        scheduled = self._task("Carosello dietro le quinte", "ALFS")
        giulia = self.people["giulia"].user

        self._row("Giulia 1: le tue task e la prima da consegnare")
        mine = (
            Issue.issue_objects.filter(
                workspace=self.workspace, issue_assignee__assignee=giulia, issue_assignee__deleted_at__isnull=True
            )
            .exclude(state__group__in=("completed", "cancelled"))
            .order_by("target_date", "name")
        )
        names = set(mine.values_list("name", flat=True))
        for issue in (autumn, cocoa, christmas, scheduled):
            self._expect(issue.name in names, f"{issue.name} non è sua")
        self._expect(any(name.startswith("Report mensile:") for name in names), "il report non è suo")
        for issue in mine:
            late = " (in ritardo)" if issue.target_date and issue.target_date < self.day else ""
            self._note(f"{issue.target_date}: {issue.name}{late}")

        self._row('Giulia 2: "Carosello ricette d\'autunno", struttura e uscita')
        choices = self._choices("giulia", autumn)
        publication = TaskDate.objects.get(issue=autumn, kind="pubblicazione").day
        self._expect(
            autumn.target_date == add_working_days(publication, -10),
            f"consegna {autumn.target_date}, uscita {publication}",
        )
        rule = (choices.get("phase") or {}).get("deadline", "")
        self._expect("10 giorni lavorativi prima" in rule, f"regola {rule!r}")

        self._row('Giulia 3: struttura di "Post lancio biscotto al cacao" finita e già mandata')
        cocoa = self._move("giulia", cocoa, "approvazione_struttura")
        self._expect(self._doers(cocoa) == {"alessandra"}, f"esecutore {self._doers(cocoa)}")
        self._expect(self._notified("alessandra", cocoa), "Alessandra senza avviso")
        self._expect(self._box("giulia", cocoa).get("status") == "da_inviare", "riquadro non da inviare")
        cocoa = self._answer("giulia", cocoa, "inviata")
        box = self._box("giulia", cocoa)
        self._expect(box.get("days_left") == 15, f"il cliente ha {box.get('days_left')} giorni")

        self._row('Giulia 4: "Post offerta di Natale" va bene, al cliente')
        christmas = self._move("giulia", christmas, "approvazione_cliente")
        self._expect(self._box("giulia", christmas).get("status") == "da_inviare", "riquadro non da inviare")
        christmas = self._answer("giulia", christmas, "inviata")
        self._expect(self._box("giulia", christmas).get("status") == "attesa", "non è in attesa del cliente")

        self._row("Giulia 5: report mensile, quali sezioni?")
        report = Issue.issue_objects.get(workspace=self.workspace, name__startswith="Report mensile:")
        found = [section for section in REPORT_SECTIONS if section in (report.description_html or "")]
        self._expect(found == list(REPORT_SECTIONS), f"sezioni {found}")
        self._note(f"{report.name}: {len(found)} sezioni.")

        self._row('Giulia 6: uscita di "Carosello dietro le quinte" una settimana dopo')
        before = TaskDate.objects.get(issue=scheduled, kind="pubblicazione").day
        later = before + timedelta(days=7)
        response = self.people["giulia"].call(
            "patch", self._atlante_url(scheduled, "scelte/"), {"pubblicazione": later.isoformat()}
        )
        self._ok(response, 200, "nuova data di pubblicazione")
        scheduled = Issue.issue_objects.get(pk=scheduled.pk)
        self._expect(scheduled.target_date == later, f"consegna {scheduled.target_date}, uscita {later}")
