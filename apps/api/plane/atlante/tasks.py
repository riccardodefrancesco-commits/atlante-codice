# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Atlante's background jobs, run by Plane's worker (plane/celery.py has their schedule)."""

from celery import shared_task

from plane.atlante import approvals
from plane.atlante.monthly_reports import create_monthly_reports


@shared_task
def monthly_reports():
    """On the first day of the month: the report task of every social project."""
    return create_monthly_reports()


@shared_task
def client_approvals():
    """Every morning: the reminder day and, from the sixteenth day, silent consent to confirm or a late yes."""
    return approvals.daily()
