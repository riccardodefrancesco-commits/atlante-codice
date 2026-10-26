# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Atlante's own tables. Plane's tables are never changed: we link to them.

- Client: the agency's client. Never deleted, only archived.
- ProjectClient: a project belongs to at most one client.
- IssueClient: a work item's own client, only in projects without a client
  (for example "Produzione video", where every item is for a different client).
- ProjectTemplate, PhaseBinding: the template a project follows and the phase
  role of each of its states (docs/specifica/08-fasi-dei-contenuti.md).
- ProjectRole, TaskRole, TaskDate, PhaseEntry: who does what in a project, the
  choices made on a single task, its dates and the log of its phases.
- TaskAssignment: since when the task has its executor, for the urgency days.
- TaskType: the kind of work of a task (video, copertina, post...).
- ClientApproval: every time a work waits for the client's OK (assaggio F, release 0.4).

The effective client of a work item is its own client if set, otherwise the
client of its project, otherwise none.
"""

import uuid

from crum import get_current_user
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from plane.db.models import BaseModel


class Client(BaseModel):
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="atlante_clients")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=12, help_text="Short code shown on cards, for example ALF")
    color = models.CharField(max_length=7, default="#3E63DD")
    internal_contact = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="atlante_followed_clients",
    )
    email = models.EmailField(blank=True, default="")
    website = models.URLField(blank=True, default="")
    internal_notes = models.TextField(blank=True, default="", help_text="Never shown to clients")
    # Revision rounds included in the client's contract (Condizioni Generali 3.0, article 8): the others are paid.
    included_revisions = models.PositiveSmallIntegerField(default=2)
    archived_at = models.DateTimeField(null=True, blank=True)
    external_source = models.CharField(max_length=255, null=True, blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "atlante_client"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "workspace",
                condition=Q(deleted_at__isnull=True),
                name="atlante_client_unique_name_per_workspace",
            ),
            models.UniqueConstraint(
                fields=["workspace", "code"],
                condition=Q(deleted_at__isnull=True),
                name="atlante_client_unique_code_per_workspace",
            ),
        ]

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class AtlanteLinkModel(models.Model):
    """Link rows: no soft delete, so filters never pick up old links.

    Changing a client updates the link; the before and after go to the
    work item history.
    """

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user is not None and not user.is_anonymous:
            if self._state.adding:
                self.created_by = user
            else:
                self.updated_by = user
        super().save(*args, **kwargs)


class ProjectClient(AtlanteLinkModel):
    project = models.OneToOneField("db.Project", on_delete=models.CASCADE, related_name="atlante_client_link")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="project_links")
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="+")

    class Meta:
        db_table = "atlante_project_client"


class IssueClient(AtlanteLinkModel):
    issue = models.OneToOneField("db.Issue", on_delete=models.CASCADE, related_name="atlante_client_link")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="issue_links")
    project = models.ForeignKey("db.Project", on_delete=models.CASCADE, related_name="+")
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="+")

    class Meta:
        db_table = "atlante_issue_client"


class ProjectTemplate(AtlanteLinkModel):
    """The template a project follows, for example "video". One per project."""

    project = models.OneToOneField("db.Project", on_delete=models.CASCADE, related_name="atlante_template")
    template = models.CharField(max_length=40)

    class Meta:
        db_table = "atlante_project_template"


class PhaseBinding(AtlanteLinkModel):
    """The phase role of a state, for example "approvazione_cliente".

    Rules look at the role, never at the name, the color or the order of the
    state: admins rename, recolor and reorder states freely (Rick, 22 October).
    """

    state = models.OneToOneField("db.State", on_delete=models.CASCADE, related_name="atlante_phase")
    project = models.ForeignKey("db.Project", on_delete=models.CASCADE, related_name="+")
    template = models.CharField(max_length=40)
    phase = models.CharField(max_length=40)

    class Meta:
        db_table = "atlante_phase_binding"
        constraints = [
            models.UniqueConstraint(fields=["project", "phase"], name="atlante_phase_binding_one_state_per_phase")
        ]


class ProjectRole(AtlanteLinkModel):
    """A person in a role of the project, for example Virginia as "editor". A role can have more people."""

    project = models.ForeignKey("db.Project", on_delete=models.CASCADE, related_name="atlante_roles")
    role = models.CharField(max_length=40)
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")

    class Meta:
        db_table = "atlante_project_role"
        constraints = [
            models.UniqueConstraint(fields=["project", "role", "member"], name="atlante_project_role_unique_member")
        ]


class TaskRole(AtlanteLinkModel):
    """A choice made on one task: its "responsabile", or people who replace the project's
    for a role (for example the editor picked by the lead videomaker)."""

    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="atlante_roles")
    role = models.CharField(max_length=40)
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")

    class Meta:
        db_table = "atlante_task_role"
        constraints = [
            models.UniqueConstraint(fields=["issue", "role", "member"], name="atlante_task_role_unique_member")
        ]


class TaskDate(AtlanteLinkModel):
    """A date of the task besides its deadline: "riprese" (shooting) or "pubblicazione"."""

    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="atlante_dates")
    kind = models.CharField(max_length=40)
    day = models.DateField()

    class Meta:
        db_table = "atlante_task_date"
        constraints = [models.UniqueConstraint(fields=["issue", "kind"], name="atlante_task_date_one_per_kind")]


class PhaseEntry(AtlanteLinkModel):
    """Every time a task enters a phase: when, who moved it (created_by), the deadline and
    the people the rule chose. The base for time spent in each phase."""

    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="atlante_phase_entries")
    state = models.ForeignKey("db.State", on_delete=models.SET_NULL, null=True, related_name="+")
    phase = models.CharField(max_length=40)
    deadline = models.DateField(null=True, blank=True)
    executor_ids = models.JSONField(default=list)
    rule = models.TextField(blank=True, default="")

    class Meta:
        db_table = "atlante_phase_entry"
        ordering = ("-created_at",)


class TaskAssignment(AtlanteLinkModel):
    """The urgency days start when someone is assigned (Rick, 22 October): the day the task got its
    executor (None while it has none) and the urgency its delivery date was counted with."""

    issue = models.OneToOneField("db.Issue", on_delete=models.CASCADE, related_name="atlante_assignment")
    assigned_on = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=30, blank=True, default="")

    class Meta:
        db_table = "atlante_task_assignment"


class TaskType(AtlanteLinkModel):
    """The kind of work of a task (project_templates.WORK_TYPES)."""

    issue = models.OneToOneField("db.Issue", on_delete=models.CASCADE, related_name="atlante_task_type")
    kind = models.CharField(max_length=30)

    class Meta:
        db_table = "atlante_task_type"


class ClientApproval(AtlanteLinkModel):
    """A work that waits for the client's OK (Condizioni Generali 3.0, articles 8 and 9.1). Until the portal
    (release 0.10) the 15 days start when someone in the team presses "Inviato al cliente" (sent_by), the
    day of sending does not count, and the silent consent is confirmed by a person (decided_by). The whole
    team of the project records the client's answer: decided_by is who recorded it."""

    READY, WAITING, APPROVED, AUTO_APPROVED, CHANGES, PASSED = (
        "da_inviare",
        "attesa",
        "approvata",
        "approvata_auto",
        "modifiche",
        "superata",
    )
    STATUSES = [
        (READY, READY),
        (WAITING, WAITING),
        (APPROVED, APPROVED),
        (AUTO_APPROVED, AUTO_APPROVED),
        (CHANGES, CHANGES),
        (PASSED, PASSED),
    ]

    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="atlante_approvals")
    state = models.ForeignKey("db.State", on_delete=models.SET_NULL, null=True, related_name="+")
    phase = models.CharField(max_length=40)
    consent = models.BooleanField(default=False, help_text="An explicit yes is needed: no silent consent")
    sent_on = models.DateField(null=True, blank=True)
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    reminder_on = models.DateField(null=True, blank=True)
    due_on = models.DateField(null=True, blank=True, help_text="The client's last day, included")
    status = models.CharField(max_length=20, choices=STATUSES, default=READY)
    round = models.PositiveSmallIntegerField(default=1)
    counts_round = models.BooleanField(default=True, help_text="Changes asked: a full round (file _2), not a micro fix")
    note = models.TextField(blank=True, default="", help_text="What the client asked")
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    next_state = models.ForeignKey("db.State", on_delete=models.SET_NULL, null=True, related_name="+")
    reminded_at = models.DateTimeField(null=True, blank=True)
    late_notice_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "atlante_client_approval"
        ordering = ("-created_at",)
