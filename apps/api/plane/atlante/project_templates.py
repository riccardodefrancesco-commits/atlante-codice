# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Project templates: the phases of each kind of work and their rules
(docs/specifica/08-fasi-dei-contenuti.md).

A template is written once here and holds for every project that follows it: one rule,
not one copy per client. In a project each phase is a Plane state, linked to its phase
role by PhaseBinding: admins rename, recolor and reorder the states, the rules stay.

Each phase says:
- who does it: a role of the project, "responsabile" (the task's), or None (nobody changes);
- when it is due:
  ("urgenza",)              working days from the task's urgency (Plane's priority);
  ("lavorativi", n)         n working days;
  ("calendario", n)         n calendar days (the client's 15 days, as in the contract);
  ("data", kind, offset)    a date of the task ("riprese", "pubblicazione") moved by
                            offset working days; without the date, the urgency counts;
  ("padre",)                the delivery date of the parent task (the cover follows its video);
  None                      the deadline does not change.
- consent: the client's OK must be explicit, no silent consent (strategy, brand and site
  presentations, article 9.1);
- back: in a phase where the work waits for the client, where "Chiedi modifiche" takes it.

The phases of Onboarding cliente are a proposal (docs/specifica/11-dai-vecchi-programmi.md):
the old acquisition procedure is not in this repository.
"""

from dataclasses import dataclass

RESPONSIBLE = "responsabile"

# The roles of a project (section 3), in the order they are shown.
ROLES = {
    "account": "Account",
    "social_media_manager": "Social media manager",
    "lead_videomaker": "Lead videomaker",
    "videomaker": "Videomaker",
    "editor": "Editor",
    "grafico": "Grafico",
    "copy": "Copy",
    "revisore_interno": "Revisore interno",
    "project_manager": "Project manager",
    "sviluppatore": "Sviluppatore web",
}

# The kind of work of a task (request 35: grouping by kind comes with release 0.5). A template
# gives its own to the tasks created in it; the cover of a video and the monthly report have theirs.
WORK_TYPES = {
    "video": "Video",
    "copertina": "Copertina",
    "post": "Post",
    "carosello": "Carosello",
    "stories": "Stories",
    "youtube": "Video YouTube",
    "grafica": "Grafica",
    "brand": "Brand",
    "sito": "Sito",
    "adv": "ADV",
    "onboarding": "Onboarding",
    "report": "Report mensile",
    "altro": "Altro",
}

# Who is the "responsabile" of a task when nobody is chosen on it, and who reviews it.
RESPONSIBLE_ROLE = "account"
REVIEWER_ROLE = "revisore_interno"

# The task dates besides the delivery date ("Consegna", Plane's target date): their name on screen
# and in the history sentences. Every task has the publication date (Rick, 22 October); a template
# can add its own.
DATES = {"riprese": "Riprese", "pubblicazione": "Pubblicazione"}
DATE_PHRASES = {"riprese": "delle riprese", "pubblicazione": "di pubblicazione"}
GENERAL_DATES = ("pubblicazione",)
# Every task has a responsible person and reviewers (request 37); a template can add roles to choose.
GENERAL_TASK_ROLES = ("revisore_interno",)

# How a role is called on a single task, when it differs from the project (glossary: "Revisori").
TASK_ROLE_NAMES = {"revisore_interno": "Revisori"}

# Urgency (section 9, Rick on 22 October): Asana's words with the days next to them, for every kind of
# work. Kept in Plane's priority field; working days after the task is assigned. New tasks start as
# Standard; a task without urgency gets no automatic delivery date.
URGENCY = {
    "urgent": ("Urgente", 1),
    "high": ("Prioritario", 3),
    "medium": ("Standard", 7),
    "low": ("In blocco", 10),
    "none": ("Nessuna", None),
}


@dataclass(frozen=True)
class Phase:
    key: str
    name: str
    group: str
    color: str
    executor: str | None = None
    deadline: tuple | None = None
    default: bool = False
    # Who does the phase when nobody is in the executor role. Without one the task is "Da assegnare".
    fallback: str | None = None
    consent: bool = False
    # A phase where the work waits for the client's OK: "Chiedi modifiche" takes the task back to this phase.
    back: str | None = None


@dataclass(frozen=True)
class Template:
    key: str
    name: str
    roles: tuple[str, ...]
    task_roles: tuple[str, ...]  # roles that can be chosen on a single task, besides the "responsabile"
    dates: tuple[str, ...]  # dates of this kind of work, besides the general ones
    phases: tuple[Phase, ...]
    work_type: str = "altro"
    # Every new task gets a cover sub-task in the phase with this key (request 36), or None.
    cover_phase: str | None = None

    def phase(self, key):
        return next((phase for phase in self.phases if phase.key == key), None)


def task_roles(template):
    """The roles chosen on a task: the general ones and the template's."""
    extra = template.task_roles if template else ()
    return GENERAL_TASK_ROLES + tuple(role for role in extra if role not in GENERAL_TASK_ROLES)


def task_dates(template):
    extra = template.dates if template else ()
    return GENERAL_DATES + tuple(kind for kind in extra if kind not in GENERAL_DATES)


# Pieces shared by every template.
START = Phase("da_pianificare", "Da pianificare", "backlog", "#60646C")
END = (Phase("fatto", "Fatto", "completed", "#46A758"), Phase("annullato", "Annullato", "cancelled", "#9AA4BC"))
# Without reviewers the responsible person reviews the work (design system, table 14).
REVIEW = Phase(
    "revisione_interna",
    "Revisione interna",
    "started",
    "#E5484D",
    "revisore_interno",
    ("lavorativi", 2),
    fallback=RESPONSIBLE,
)
# The client approves from the portal (release 0.10): until then the responsible person follows it.
CLIENT_DAYS = ("calendario", 15)


def client_ok(key, name, back, consent=False):
    """A phase where the work waits for the client: "Approva" goes to the next phase, "Chiedi
    modifiche" goes back to `back`, with the same urgency."""
    return Phase(key, name, "started", "#8E4EC6", RESPONSIBLE, CLIENT_DAYS, consent=consent, back=back)


def scheduled(executor="social_media_manager"):
    return Phase(
        "pubblicazione", "Schedulato o pubblicato", "started", "#12A594", executor, ("data", "pubblicazione", 0)
    )


# The cover of a video (section 6): a sub-task in the video's project, done by the graphic designer by
# the video's delivery date, then the same review and approval as the video.
COVER = Phase("grafica_copertina", "Copertina in grafica", "started", "#D6409F", "grafico", ("padre",))

SOCIAL_ROLES = ("account", "social_media_manager", "grafico", "revisore_interno", "project_manager")
VIDEO_ROLES = ("account", "social_media_manager", "lead_videomaker", "videomaker", "editor", "grafico")

VIDEO = Template(
    key="video",
    name="Video e reel",
    roles=(*VIDEO_ROLES, "revisore_interno", "project_manager"),
    # The reviewers of the task (request 37) and the editor, chosen by the lead videomaker in "Girato".
    task_roles=("revisore_interno", "editor"),
    dates=("riprese",),
    work_type="video",
    cover_phase="grafica_copertina",
    phases=(
        START,
        Phase(
            "script",
            "Script",
            "unstarted",
            "#8B8D98",
            executor="social_media_manager",
            deadline=("data", "riprese", -2),
            default=True,
        ),
        client_ok("approvazione_script", "Approvazione script", "script"),
        Phase("da_girare", "Da girare", "started", "#3E63DD", "videomaker", ("data", "riprese", 0)),
        Phase("girato", "Girato", "started", "#0090FF", "lead_videomaker", ("urgenza",)),
        Phase("montaggio", "In montaggio", "started", "#F59E0B", "editor", ("urgenza",)),
        COVER,
        REVIEW,
        client_ok("approvazione_cliente", "Approvazione cliente", "montaggio"),
        # With every channel ticked the task is published (release 0.6): until then it is closed by hand.
        scheduled(),
        *END,
    ),
)

YOUTUBE = Template(
    key="youtube",
    name="Video YouTube",
    roles=(*VIDEO_ROLES, "revisore_interno", "project_manager"),
    task_roles=("revisore_interno", "editor"),
    dates=("riprese",),
    work_type="youtube",
    cover_phase="grafica_copertina",
    phases=(
        START,
        # Section 8: the common scheme with the pre-production before the script.
        Phase("preproduzione", "Preproduzione", "unstarted", "#8B8D98", "lead_videomaker", ("urgenza",), default=True),
        Phase("script", "Script", "started", "#6E56CF", "social_media_manager", ("data", "riprese", -2)),
        client_ok("approvazione_script", "Approvazione script", "script"),
        Phase("da_girare", "Da girare", "started", "#3E63DD", "videomaker", ("data", "riprese", 0)),
        Phase("girato", "Girato", "started", "#0090FF", "lead_videomaker", ("urgenza",)),
        Phase("montaggio", "In montaggio", "started", "#F59E0B", "editor", ("urgenza",)),
        COVER,
        REVIEW,
        client_ok("approvazione_cliente", "Approvazione cliente", "montaggio"),
        scheduled(),
        *END,
    ),
)

POST = Template(
    key="post",
    name="Post e caroselli",
    roles=SOCIAL_ROLES,
    task_roles=("revisore_interno",),
    dates=(),
    work_type="post",
    phases=(
        START,
        # Proposal (section 5): counted back from the publication date, 10 working days before.
        Phase(
            "struttura",
            "Struttura del post",
            "unstarted",
            "#8B8D98",
            "social_media_manager",
            ("data", "pubblicazione", -10),
            default=True,
        ),
        client_ok("approvazione_struttura", "Approvazione struttura", "struttura"),
        Phase("grafica", "In grafica", "started", "#F59E0B", "grafico", ("urgenza",)),
        REVIEW,
        client_ok("approvazione_cliente", "Approvazione cliente", "grafica"),
        scheduled(),
        *END,
    ),
)

SITE = Template(
    key="sito",
    name="Sito web",
    roles=("account", "grafico", "copy", "sviluppatore", "revisore_interno", "project_manager"),
    task_roles=("revisore_interno",),
    dates=(),
    work_type="sito",
    # Section 7: about 5-6 weeks to go online, plus 2 weeks of bug checks. Weeks as working days.
    phases=(
        START,
        Phase("analisi", "Analisi preliminare", "unstarted", "#8B8D98", "account", ("lavorativi", 3), default=True),
        Phase("design_copy", "Design e copy", "started", "#6E56CF", "grafico", ("lavorativi", 10)),
        client_ok("presentazione", "Presentazione al cliente", "design_copy", consent=True),
        Phase("raccolta_tecnica", "Raccolta tecnica", "started", "#0090FF", "account", ("lavorativi", 5)),
        Phase("ambiente", "Preparazione dell'ambiente", "started", "#3E63DD", "sviluppatore", ("lavorativi", 3)),
        Phase("produzione", "Produzione", "started", "#F59E0B", "sviluppatore", ("lavorativi", 15)),
        REVIEW,
        client_ok("approvazione_cliente", "Approvazione cliente", "produzione", consent=True),
        Phase("messa_online", "Messa online", "started", "#12A594", "sviluppatore", ("lavorativi", 1)),
        Phase("controllo_bug", "Controllo bug", "started", "#46A758", "sviluppatore", ("lavorativi", 10)),
        *END,
    ),
)

BRAND = Template(
    key="brand",
    name="Brand",
    roles=("account", "grafico", "revisore_interno", "project_manager"),
    task_roles=("revisore_interno",),
    dates=(),
    work_type="brand",
    # Section 8: about 9 weeks, an explicit OK of the client at every step (base and intermediate
    # brand have the same phases, with less material).
    phases=(
        START,
        Phase("brief", "Call di brief", "unstarted", "#8B8D98", "account", ("lavorativi", 1), default=True),
        Phase("analisi", "Analisi strategica", "started", "#6E56CF", "grafico", ("lavorativi", 5)),
        client_ok("ok_analisi", "Ok all'analisi", "analisi", consent=True),
        Phase("direzione", "Direzione creativa", "started", "#0090FF", "grafico", ("lavorativi", 5)),
        client_ok("ok_direzione", "Ok alla direzione creativa", "direzione", consent=True),
        Phase("logo", "Logo, tipografia e colori", "started", "#3E63DD", "grafico", ("lavorativi", 10)),
        client_ok("ok_logo", "Ok al logo", "logo", consent=True),
        Phase("coordinata", "Immagine coordinata", "started", "#F59E0B", "grafico", ("lavorativi", 5)),
        Phase("asset", "Asset", "started", "#D6409F", "grafico", ("lavorativi", 5)),
        Phase("manual", "Brand manual", "started", "#12A594", "grafico", ("lavorativi", 10)),
        client_ok("approvazione_cliente", "Approvazione finale", "manual", consent=True),
        *END,
    ),
)

GRAPHIC = Template(
    key="grafica",
    name="Grafica singola",
    roles=("account", "grafico", "revisore_interno", "project_manager"),
    task_roles=("revisore_interno",),
    dates=(),
    work_type="grafica",
    # Section 8: locandine and flyer, about 1 week for the simple ones.
    phases=(
        START,
        Phase(
            "informazioni",
            "Informazioni dal cliente",
            "unstarted",
            "#8B8D98",
            "account",
            ("lavorativi", 2),
            default=True,
        ),
        Phase("direzione", "Direzione artistica", "started", "#6E56CF", "grafico", ("lavorativi", 2)),
        client_ok("ok_direzione", "Ok alla direzione", "direzione"),
        Phase("produzione", "Produzione", "started", "#F59E0B", "grafico", ("urgenza",)),
        REVIEW,
        client_ok("approvazione_cliente", "Approvazione cliente", "produzione"),
        Phase("consegna", "Stampa o consegna", "started", "#12A594", "account", ("lavorativi", 2)),
        *END,
    ),
)

ADV = Template(
    key="adv",
    name="ADV online",
    roles=SOCIAL_ROLES,
    task_roles=("revisore_interno",),
    dates=(),
    work_type="adv",
    # Section 8: the common scheme with strategy and budget; the strategy needs an explicit OK.
    phases=(
        START,
        Phase(
            "informazioni", "Raccolta informazioni", "unstarted", "#8B8D98", "account", ("lavorativi", 3), default=True
        ),
        Phase("strategia", "Strategia e budget", "started", "#6E56CF", "social_media_manager", ("lavorativi", 5)),
        client_ok("ok_strategia", "Ok alla strategia", "strategia", consent=True),
        Phase("creativita", "Creatività", "started", "#F59E0B", "grafico", ("urgenza",)),
        REVIEW,
        client_ok("approvazione_cliente", "Approvazione cliente", "creativita"),
        Phase(
            "campagna", "Campagna attiva", "started", "#12A594", "social_media_manager", ("data", "pubblicazione", 0)
        ),
        *END,
    ),
)

ONBOARDING = Template(
    key="onboarding",
    name="Onboarding cliente (proposta)",
    roles=("account", "social_media_manager", "project_manager"),
    task_roles=("revisore_interno",),
    dates=(),
    work_type="onboarding",
    # Proposal, to confirm with the acquisition procedure of the old programs (phase 8).
    phases=(
        START,
        Phase("benvenuto", "Benvenuto e contratto", "unstarted", "#8B8D98", "account", ("lavorativi", 2), default=True),
        Phase("questionario", "Questionario del brand", "started", "#6E56CF", RESPONSIBLE, CLIENT_DAYS),
        Phase("materiali", "Materiali e accessi", "started", "#0090FF", "account", ("lavorativi", 5)),
        Phase("avvio", "Call di avvio", "started", "#3E63DD", "project_manager", ("lavorativi", 3)),
        Phase("piano", "Piano del primo mese", "started", "#F59E0B", "social_media_manager", ("lavorativi", 5)),
        client_ok("approvazione_cliente", "Ok al piano", "piano", consent=True),
        *END,
    ),
)

TEMPLATES = {template.key: template for template in (VIDEO, POST, YOUTUBE, GRAPHIC, BRAND, SITE, ADV, ONBOARDING)}
