# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Client rules shared by the interface API, the public API and (later) the
Claude port and automations: one place only."""

from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from django.db.models import Case, Count, F, IntegerField, Prefetch, Q, Value, When

from plane.atlante.models import IssueClient, ProjectClient
from django.utils import timezone

from plane.db.models import Issue, IssueActivity, IssueAssignee, ProjectMember

CLOSED_GROUPS = ("completed", "cancelled")
OPEN_FILTER = ~Q(state__group__in=CLOSED_GROUPS)


def workspace_today(workspace):
    """Today's date in the workspace's timezone (Zeta3: Europe/Rome)."""
    try:
        tz = ZoneInfo(workspace.timezone or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz).date()


def active_project_links(workspace):
    """Links to projects that still exist (Plane soft-deletes projects)."""
    return ProjectClient.objects.filter(workspace=workspace, project__deleted_at__isnull=True)


def effective_client_id(issue):
    """The client of a work item: its own, else its project's, else None."""
    own = IssueClient.objects.filter(issue=issue).values_list("client_id", flat=True).first()
    if own:
        return own
    return (
        ProjectClient.objects.filter(project_id=issue.project_id, project__deleted_at__isnull=True)
        .values_list("client_id", flat=True)
        .first()
    )


def _issue_counts(queryset, group_field, today):
    return queryset.values(group_field).annotate(
        total=Count("id"),
        completed=Count("id", filter=Q(state__group="completed")),
        open=Count("id", filter=OPEN_FILTER),
        overdue=Count("id", filter=OPEN_FILTER & Q(target_date__lt=today)),
    )


def client_stats(workspace):
    """For every client: active projects, open and overdue work items."""
    today = workspace_today(workspace)
    stats = defaultdict(lambda: {"project_count": 0, "open_issues": 0, "overdue_issues": 0})

    project_to_client = dict(
        active_project_links(workspace).filter(project__archived_at__isnull=True).values_list("project_id", "client_id")
    )
    for client_id in project_to_client.values():
        stats[client_id]["project_count"] += 1

    issues = Issue.issue_objects.filter(workspace=workspace)
    for row in _issue_counts(issues.filter(project_id__in=project_to_client.keys()), "project_id", today):
        bucket = stats[project_to_client[row["project_id"]]]
        bucket["open_issues"] += row["open"]
        bucket["overdue_issues"] += row["overdue"]

    own = issues.filter(atlante_client_link__isnull=False)
    for row in _issue_counts(own, "atlante_client_link__client_id", today):
        bucket = stats[row["atlante_client_link__client_id"]]
        bucket["open_issues"] += row["open"]
        bucket["overdue_issues"] += row["overdue"]

    return stats


def client_projects(workspace, client):
    """The projects of a client, with progress."""
    today = workspace_today(workspace)
    links = active_project_links(workspace).filter(client=client).select_related("project")
    projects = {link.project_id: link.project for link in links}
    counts = {
        row["project_id"]: row
        for row in _issue_counts(
            Issue.issue_objects.filter(project_id__in=projects.keys()), "project_id", today
        )
    }
    result = []
    for project_id, project in projects.items():
        row = counts.get(project_id, {})
        result.append(
            {
                "id": project.id,
                "name": project.name,
                "identifier": project.identifier,
                "archived_at": project.archived_at,
                "total_issues": row.get("total", 0),
                "completed_issues": row.get("completed", 0),
                "open_issues": row.get("open", 0),
                "overdue_issues": row.get("overdue", 0),
            }
        )
    return sorted(result, key=lambda p: p["name"].lower())


STATE_GROUP_ORDER = ("backlog", "unstarted", "started", "completed", "cancelled")
CLIENT_ISSUES_LIMIT = 500


def visible_project_filter(workspace, user):
    """The work items a person may see, with Plane's own rule: everything in the
    projects where they are a member; in projects where they are a guest, only
    what they created, unless the project lets guests see everything."""
    memberships = ProjectMember.objects.filter(
        workspace=workspace, member=user, is_active=True, project__deleted_at__isnull=True
    )
    full = memberships.filter(Q(role__gt=5) | Q(role=5, project__guest_view_all_features=True)).values("project_id")
    limited = memberships.filter(role=5, project__guest_view_all_features=False).values("project_id")
    return Q(project_id__in=full) | Q(project_id__in=limited, created_by=user)


def client_issues(workspace, client, user, limit=CLIENT_ISSUES_LIMIT):
    """The work items of a client, from all its projects and from projects
    without a client (its own items), that the person may see.

    Ordered by phase group (to do first), then due date. The counts cover all of
    them, even beyond the limit of the list."""
    today = workspace_today(workspace)
    project_ids = active_project_links(workspace).filter(client=client).values("project_id")
    issues = (
        Issue.issue_objects.filter(workspace=workspace)
        .filter(Q(project_id__in=project_ids) | Q(atlante_client_link__client=client))
        .filter(visible_project_filter(workspace, user))
    )
    counts = {group: 0 for group in STATE_GROUP_ORDER}
    for row in issues.values("state__group").annotate(n=Count("id")):
        if row["state__group"] in counts:
            counts[row["state__group"]] += row["n"]
    overdue = issues.filter(OPEN_FILTER & Q(target_date__lt=today)).count()

    group_order = Case(
        *[When(state__group=group, then=Value(i)) for i, group in enumerate(STATE_GROUP_ORDER)],
        default=Value(len(STATE_GROUP_ORDER)),
        output_field=IntegerField(),
    )
    rows = (
        issues.select_related("project", "state")
        .prefetch_related(Prefetch("issue_assignee", queryset=IssueAssignee.objects.all()))
        .annotate(group_order=group_order)
        .order_by("group_order", F("target_date").asc(nulls_last=True), "-created_at")[:limit]
    )
    results = []
    for issue in rows:
        is_open = issue.state is None or issue.state.group not in CLOSED_GROUPS
        results.append(
            {
                "id": issue.id,
                "name": issue.name,
                "sequence_id": issue.sequence_id,
                "project_id": issue.project_id,
                "project_identifier": issue.project.identifier,
                "project_name": issue.project.name,
                "state_name": issue.state.name if issue.state else None,
                "state_group": issue.state.group if issue.state else None,
                "state_color": issue.state.color if issue.state else None,
                "priority": issue.priority,
                "target_date": issue.target_date,
                "overdue": bool(is_open and issue.target_date and issue.target_date < today),
                "assignee_ids": [a.assignee_id for a in issue.issue_assignee.all()],
            }
        )
    total = sum(counts.values())
    return {"total": total, "overdue": overdue, "counts": counts, "truncated": total > len(results), "results": results}


def record_client_activity(issue, actor, old_client, new_client):
    """One line in the work item history (Plane's IssueActivity): who changed
    the client, from what to what. The interface shows it in pezzo 6."""
    IssueActivity.objects.create(
        issue=issue,
        project_id=issue.project_id,
        workspace_id=issue.workspace_id,
        actor=actor,
        verb="updated",
        field="atlante_client",
        old_value=old_client.name if old_client else None,
        new_value=new_client.name if new_client else None,
        old_identifier=old_client.id if old_client else None,
        new_identifier=new_client.id if new_client else None,
        comment="updated the client to" if new_client else "removed the client",
        epoch=int(timezone.now().timestamp()),
    )
