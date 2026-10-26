# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from plane.atlante.phases import enter_phase, task_saved
from plane.db.models import Issue
from plane.license.models import Instance


@receiver(pre_save, sender=Instance)
def keep_telemetry_disabled(sender, instance, **kwargs):
    """Atlante never sends usage data to Plane.

    Plane turns telemetry on by default (model default, first-run admin form,
    admin settings). Whatever path saves the instance, the flag stays off.
    """
    instance.is_telemetry_enabled = False


@receiver(post_save, sender=Issue)
def run_phase_rule(sender, instance, created, raw=False, **kwargs):
    """A task moved to another phase: the rule of the phase picks executor and delivery date.
    Any other change: someone assigned by hand, or a new urgency, sets the delivery date.

    Any path that saves the task counts (board, list, task page, API). Plane's serializer sets
    the assignees before saving, so the rule has the last word. A new task is handled at the
    end of its creation (enter_phase(created=True) in Plane's serializers), so that the people
    chosen in the form are already there.
    """
    if raw or created:
        return
    if "state_id" in (getattr(instance, "_changes_on_save", None) or ()):
        enter_phase(instance)
    else:
        task_saved(instance)
