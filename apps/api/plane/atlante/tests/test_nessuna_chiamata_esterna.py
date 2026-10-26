# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Atlante never calls Plane's servers.

If an update from Plane turns telemetry or the version check back on,
these tests fail.
"""

import secrets
from unittest import mock

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from plane.license.models import Instance


def _fail_if_called(*args, **kwargs):
    raise AssertionError(f"Unexpected outbound call: {args} {kwargs}")


@pytest.mark.unit
def test_no_telemetry_in_periodic_schedule():
    from plane.celery import app

    tasks = [entry["task"] for entry in app.conf.beat_schedule.values()]
    assert not [task for task in tasks if "telemetry" in task]


@pytest.mark.unit
@pytest.mark.django_db
def test_startup_registration_makes_no_outbound_calls():
    with (
        mock.patch("requests.get", side_effect=_fail_if_called),
        mock.patch("requests.post", side_effect=_fail_if_called),
        mock.patch(
            "plane.license.bgtasks.telemetry_metrics.push_instance_metrics.delay",
            side_effect=_fail_if_called,
        ),
    ):
        call_command("register_instance", "firma-di-prova")

    instance = Instance.objects.get()
    assert instance.is_telemetry_enabled is False


@pytest.mark.unit
@pytest.mark.django_db
def test_telemetry_flag_cannot_be_turned_on():
    instance = Instance.objects.create(
        instance_name="Atlante prova",
        instance_id=secrets.token_hex(12),
        current_version="1.0.0",
        latest_version="1.0.0",
        last_checked_at=timezone.now(),
        is_telemetry_enabled=True,
    )
    instance.refresh_from_db()
    assert instance.is_telemetry_enabled is False

    instance.is_telemetry_enabled = True
    instance.save()
    instance.refresh_from_db()
    assert instance.is_telemetry_enabled is False


@pytest.mark.contract
@pytest.mark.django_db
def test_no_product_updates_page_from_plane():
    cache.clear()
    Instance.objects.create(
        instance_name="Atlante prova",
        instance_id=secrets.token_hex(12),
        current_version="1.0.0",
        latest_version="1.0.0",
        last_checked_at=timezone.now(),
    )
    response = APIClient().get("/api/instances/")
    assert response.status_code == 200
    assert response.json()["config"]["instance_changelog_url"] == ""
