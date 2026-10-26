#!/bin/sh
# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
#
# Tests of Atlante's interface code. Vitest is the one Plane already installs for @plane/blocks:
# no Plane file or library list changes.
cd "$(dirname "$0")/../.." || exit 1
exec packages/blocks/node_modules/.bin/vitest run --config atlante/test-interfaccia/vitest.config.mjs --root . "$@"
