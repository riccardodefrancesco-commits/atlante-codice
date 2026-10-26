# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import re

from rest_framework import serializers

from plane.app.serializers.base import BaseSerializer
from plane.atlante.models import Client
from plane.db.models import User, WorkspaceMember

CODE_RE = re.compile(r"^[A-Za-z0-9]{1,12}$")
COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
MEMBER_ROLES = (15, 20)


class ClientSerializer(BaseSerializer):
    internal_contact = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "code",
            "color",
            "internal_contact",
            "email",
            "website",
            "internal_notes",
            "included_revisions",
            "archived_at",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = ["id", "archived_at", "created_at", "updated_at", "created_by"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Il nome del cliente è obbligatorio.")
        return value

    def validate_code(self, value):
        value = value.strip()
        if not CODE_RE.match(value):
            raise serializers.ValidationError("La sigla va da 1 a 12 lettere o numeri, senza spazi.")
        return value.upper()

    def validate_color(self, value):
        if not COLOR_RE.match(value):
            raise serializers.ValidationError("Il colore va scritto come #RRGGBB, per esempio #3E63DD.")
        return value.upper()

    def validate_included_revisions(self, value):
        if value > 20:
            raise serializers.ValidationError("I giri di revisione inclusi vanno da 0 a 20.")
        return value

    def validate_internal_contact(self, user):
        if user is None:
            return user
        workspace = self.context["workspace"]
        is_team = WorkspaceMember.objects.filter(
            workspace=workspace, member=user, is_active=True, role__in=MEMBER_ROLES
        ).exists()
        if not is_team:
            raise serializers.ValidationError("Il referente deve essere una persona del team in questo spazio.")
        return user

    def validate(self, attrs):
        workspace = self.context["workspace"]
        others = Client.objects.filter(workspace=workspace)
        if self.instance is not None:
            others = others.exclude(pk=self.instance.pk)
        name = attrs.get("name")
        if name and others.filter(name__iexact=name).exists():
            raise serializers.ValidationError({"name": "Esiste già un cliente con questo nome."})
        code = attrs.get("code")
        if code and others.filter(code=code).exists():
            raise serializers.ValidationError({"code": "Esiste già un cliente con questa sigla."})
        return attrs
