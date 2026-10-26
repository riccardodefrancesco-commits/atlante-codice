# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Section 3 of the online trial ("Cosa deve succedere") holds on the prepared data, and checking it
leaves no trace: same tasks, same answers of the client, no notice for anybody."""

from io import StringIO

import pytest
from django.core.management import call_command

from plane.atlante.models import ClientApproval
from plane.db.models import Issue, IssueActivity, Notification, Project


@pytest.mark.unit
@pytest.mark.django_db
def test_every_row_of_section_3_holds_and_nothing_changes(instance, people_file):
    call_command("atlante_dati_collaudo", persone=people_file)
    before = {
        "tasks": Issue.issue_objects.filter(workspace__slug="zeta3-collaudo").count(),
        "projects": Project.objects.filter(workspace__slug="zeta3-collaudo").count(),
        "answers": list(ClientApproval.objects.order_by("id").values_list("status", flat=True)),
        "history": IssueActivity.objects.count(),
        "notices": Notification.objects.filter(read_at__isnull=True).count(),
    }
    out = StringIO()

    call_command("atlante_verifica_collaudo", stdout=out)

    report = out.getvalue()
    assert "NO " not in report, report
    assert report.count("OK ") == 8 + 7 + 4 + 6, report
    after = {
        "tasks": Issue.issue_objects.filter(workspace__slug="zeta3-collaudo").count(),
        "projects": Project.objects.filter(workspace__slug="zeta3-collaudo").count(),
        "answers": list(ClientApproval.objects.order_by("id").values_list("status", flat=True)),
        "history": IssueActivity.objects.count(),
        "notices": Notification.objects.filter(read_at__isnull=True).count(),
    }
    assert after == before
