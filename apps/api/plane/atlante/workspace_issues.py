# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The workspace's "all work items" also as list and board, for the agency board
(columns by phase, rows by client).

In free Plane that view is a table only and its server answers without groups.
This class keeps all of Plane's view (who sees what, filters, annotations) and adds
the groups the same way Plane already does on the "your work" page. Without
group_by it is Plane's own answer, plus the client of each work item.

It answers on Plane's own address (registered before Plane's in plane/urls.py), so
Plane's interface keeps using its own service.
"""

import copy

from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.view.base import WorkspaceViewIssuesViewSet
from plane.atlante.grouping import APPROVAL_FIELD, CLIENT_FIELD, PUBLISH_FIELD, WORK_TYPE_FIELD, annotate_atlante_fields
from plane.utils.grouper import issue_group_values, issue_on_results, issue_queryset_grouper
from plane.utils.issue_filters import issue_filters
from plane.utils.order_queryset import order_issue_queryset
from plane.utils.paginator import GroupedOffsetPaginator, SubGroupedOffsetPaginator

# The same count rule Plane uses for grouped lists (no drafts, no archived, intake only if accepted).
COUNT_FILTER = Q(
    Q(issue_intake__status=1) | Q(issue_intake__status=-1) | Q(issue_intake__status=2) | Q(issue_intake__isnull=True),
    archived_at__isnull=True,
    is_draft=False,
)


def _with_client(on_results):
    """Plane's table rows do not carry Atlante's fields (client, publication date, kind of work): add them."""

    def results(issues):
        rows = on_results(issues)
        for row, issue in zip(rows, issues):
            client_id = getattr(issue, CLIENT_FIELD, None)
            row[CLIENT_FIELD] = str(client_id) if client_id else None
            publish = getattr(issue, PUBLISH_FIELD, None)
            row[PUBLISH_FIELD] = publish.isoformat() if publish else None
            row[WORK_TYPE_FIELD] = getattr(issue, WORK_TYPE_FIELD, None)
            due = getattr(issue, APPROVAL_FIELD, None)
            row[APPROVAL_FIELD] = due.isoformat() if due else None
        return rows

    return results


class AtlanteWorkspaceIssuesViewSet(WorkspaceViewIssuesViewSet):
    def apply_annotations(self, issues):
        return annotate_atlante_fields(super().apply_annotations(issues))

    def paginate(self, *args, **kwargs):
        if kwargs.get("paginator_cls") is None and kwargs.get("on_results") is not None:
            kwargs["on_results"] = _with_client(kwargs["on_results"])
        return super().paginate(*args, **kwargs)

    @method_decorator(gzip_page)
    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def list(self, request, slug):
        group_by = request.GET.get("group_by", False)
        if not group_by:
            return super().list(request, slug=slug)
        sub_group_by = request.GET.get("sub_group_by", False)
        if group_by == sub_group_by:
            return Response(
                {"error": "Group by and sub group by cannot have same parameters"}, status=status.HTTP_400_BAD_REQUEST
            )

        # The same steps as Plane's own list: filters, who sees what, order.
        issue_queryset = self.filter_queryset(self.get_queryset())
        filters = issue_filters(request.query_params, "GET")
        issue_queryset = issue_queryset.filter(**filters).filter(self._get_project_permission_filters())
        total_issue_queryset = copy.deepcopy(issue_queryset).only("id")
        issue_queryset = self.apply_annotations(issue_queryset)
        issue_queryset, order_by_param = order_issue_queryset(
            issue_queryset=issue_queryset, order_by_param=request.GET.get("order_by", "-created_at")
        )
        issue_queryset = issue_queryset_grouper(queryset=issue_queryset, group_by=group_by, sub_group_by=sub_group_by)

        def group_values(field):
            return issue_group_values(
                field=field, slug=slug, filters=filters, queryset=total_issue_queryset, user=request.user
            )

        common = {
            "request": request,
            "order_by": order_by_param,
            "queryset": issue_queryset,
            "total_count_queryset": total_issue_queryset,
            "on_results": lambda issues: issue_on_results(group_by=group_by, issues=issues, sub_group_by=sub_group_by),
            "group_by_fields": group_values(group_by),
            "group_by_field_name": group_by,
            "count_filter": COUNT_FILTER,
        }
        if sub_group_by:
            return self.paginate(
                paginator_cls=SubGroupedOffsetPaginator,
                sub_group_by_fields=group_values(sub_group_by),
                sub_group_by_field_name=sub_group_by,
                **common,
            )
        return self.paginate(paginator_cls=GroupedOffsetPaginator, **common)
