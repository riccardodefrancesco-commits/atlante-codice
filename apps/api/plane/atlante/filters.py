# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Client filters for Plane's work item filter set.

Plane's IssueFilterSet inherits from AtlanteClientFilterSet, so the rich
filters accept: client_id, client_id__in and client_id__isnull. The client is
the effective one: the work item's own, else its project's.
"""

import django_filters as filters
from django.db.models import Q


class UUIDInFilter(filters.BaseInFilter, filters.UUIDFilter):
    pass


def _client_in(ids):
    return Q(atlante_client_link__client_id__in=ids) | Q(
        atlante_client_link__isnull=True, project__atlante_client_link__client_id__in=ids
    )


def _no_client():
    return Q(atlante_client_link__isnull=True, project__atlante_client_link__isnull=True)


class AtlanteClientFilterSet(filters.FilterSet):
    client_id = filters.UUIDFilter(method="filter_client_id")
    client_id__in = UUIDInFilter(method="filter_client_id_in", lookup_expr="in")
    client_id__isnull = filters.BooleanFilter(method="filter_client_id_isnull")

    def filter_client_id(self, queryset, name, value):
        return _client_in([value])

    def filter_client_id_in(self, queryset, name, value):
        return _client_in(value)

    def filter_client_id_isnull(self, queryset, name, value):
        if value is None:
            return Q()
        return _no_client() if value else ~_no_client()


def filter_atlante_client(params, issue_filter, method, prefix=""):
    """Legacy filter used by Plane's interface to load more items of one group:
    atlante_client=<client id>[,<client id>][,None]."""
    import uuid

    from plane.db.models import Issue

    raw = params.get("atlante_client")
    values = raw.split(",") if isinstance(raw, str) else list(raw or [])
    condition = Q()
    if "None" in values:
        condition |= _no_client()
    ids = []
    for value in values:
        try:
            ids.append(str(uuid.UUID(str(value))))
        except ValueError:
            continue
    if ids:
        condition |= _client_in(ids)
    if condition:
        issue_filter[f"{prefix}id__in"] = Issue.all_objects.filter(condition).values("id")
    return issue_filter
