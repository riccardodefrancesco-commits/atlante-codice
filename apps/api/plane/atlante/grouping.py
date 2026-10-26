# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The client and the publication date inside Plane's work item lists.

Plane's grouper (plane/utils/grouper.py) calls these functions, so every list
that goes through it (project, cycle, module, archived, profile work items)
returns `atlante_client_id`, which it can be grouped by (group_by=atlante_client_id),
`atlante_publish_date`, the second date of every task (Rick, 22 October), and
`atlante_work_type`, the kind of work.
"""

from django.db.models import CharField, DateField, F, OuterRef, Subquery, UUIDField
from django.db.models.functions import Coalesce

from plane.atlante.models import Client, ClientApproval, IssueClient, ProjectClient, TaskDate, TaskType

CLIENT_FIELD = "atlante_client_id"
PUBLISH_FIELD = "atlante_publish_date"
WORK_TYPE_FIELD = "atlante_work_type"
APPROVAL_FIELD = "atlante_approval_due"
# The fields Atlante adds to every task in the lists.
LIST_FIELDS = (CLIENT_FIELD, PUBLISH_FIELD, WORK_TYPE_FIELD, APPROVAL_FIELD)

# Fixed names added to Plane's security allowlist of grouping fields (GHSA-wwgj-929g-42cm).
ATLANTE_GROUP_BY_ALLOWLIST = frozenset({CLIENT_FIELD})


def effective_client_expression():
    """The work item's own client, else its project's client, else NULL."""
    own = IssueClient.objects.filter(issue_id=OuterRef("pk")).values("client_id")[:1]
    of_project = ProjectClient.objects.filter(project_id=OuterRef("project_id")).values("client_id")[:1]
    return Coalesce(
        Subquery(own, output_field=UUIDField()),
        Subquery(of_project, output_field=UUIDField()),
        output_field=UUIDField(),
    )


def publish_date_expression():
    day = TaskDate.objects.filter(issue_id=OuterRef("pk"), kind="pubblicazione").values("day")[:1]
    return Subquery(day, output_field=DateField())


def work_type_expression():
    kind = TaskType.objects.filter(issue_id=OuterRef("pk")).values("kind")[:1]
    return Subquery(kind, output_field=CharField())


def approval_due_expression():
    """The last day the client has to answer, while the task waits for it in its phase."""
    due = ClientApproval.objects.filter(
        issue_id=OuterRef("pk"), state_id=OuterRef("state_id"), status=ClientApproval.WAITING
    ).values("due_on")[:1]
    return Subquery(due, output_field=DateField())


def annotate_atlante_fields(queryset):
    """Client, publication date and kind of work of each task, once."""
    missing = {}
    if CLIENT_FIELD not in queryset.query.annotations:
        missing[CLIENT_FIELD] = effective_client_expression()
    if PUBLISH_FIELD not in queryset.query.annotations:
        missing[PUBLISH_FIELD] = publish_date_expression()
    if WORK_TYPE_FIELD not in queryset.query.annotations:
        missing[WORK_TYPE_FIELD] = work_type_expression()
    if APPROVAL_FIELD not in queryset.query.annotations:
        missing[APPROVAL_FIELD] = approval_due_expression()
    return queryset.annotate(**missing) if missing else queryset


def client_group_values(slug, project_id=None):
    """The groups shown when grouping by client, plus "None" for no client."""
    if project_id:
        ids = set(IssueClient.objects.filter(project_id=project_id).values_list("client_id", flat=True))
        ids |= set(ProjectClient.objects.filter(project_id=project_id).values_list("client_id", flat=True))
    else:
        ids = set(Client.objects.filter(workspace__slug=slug).values_list("id", flat=True))
    return list(ids) + ["None"]


# Ordering the table by client name: order_by=atlante_client__name (or with "-").
CLIENT_ORDER_KEYS = ("atlante_client__name", "-atlante_client__name")


def order_by_client(queryset, order_by_param):
    """Order by the effective client's name, items without client last.

    Returns the queryset and the key that Plane's paginator orders on, like
    Plane's own special orderings (priority, state)."""
    own = IssueClient.objects.filter(issue_id=OuterRef("pk")).values("client__name")[:1]
    of_project = ProjectClient.objects.filter(project_id=OuterRef("project_id")).values("client__name")[:1]
    queryset = queryset.annotate(
        atlante_client_name=Coalesce(
            Subquery(own, output_field=CharField()),
            Subquery(of_project, output_field=CharField()),
            output_field=CharField(),
        )
    )
    descending = order_by_param.startswith("-")
    name = F("atlante_client_name")
    queryset = queryset.order_by(name.desc(nulls_last=True) if descending else name.asc(nulls_last=True), "-created_at")
    return queryset, "-atlante_client_name" if descending else "atlante_client_name"
