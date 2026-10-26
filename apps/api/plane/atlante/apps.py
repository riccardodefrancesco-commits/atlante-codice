# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.apps import AppConfig


class AtlanteConfig(AppConfig):
    name = "plane.atlante"
    label = "atlante"
    verbose_name = "Atlante"

    def ready(self):
        # Registers the signal handlers (telemetry always off, phase rules).
        from plane.atlante import signals  # noqa: F401
