# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Creates now the report tasks of the month just ended (the worker does it on the first day of the month).

Usage, inside the api container:
    python manage.py atlante_report_mensili
"""

from django.core.management.base import BaseCommand

from plane.atlante.monthly_reports import create_monthly_reports


class Command(BaseCommand):
    help = "Crea le task del report mensile nei progetti social (una volta al mese)."

    def handle(self, *args, **options):
        created = create_monthly_reports()
        self.stdout.write(self.style.SUCCESS(f"Task del report create: {created}."))
