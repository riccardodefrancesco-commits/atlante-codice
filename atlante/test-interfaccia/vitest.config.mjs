/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tests of Atlante's interface code (apps/web/atlante). They stay outside apps/web, so Plane's
 * type check and configuration are untouched. Run with: atlante/script/test-interfaccia.sh
 */

import { fileURLToPath } from "node:url";

const web = fileURLToPath(new URL("../../apps/web/", import.meta.url));

export default {
  resolve: {
    alias: [{ find: /^@\//, replacement: web }],
  },
  test: {
    globals: true,
    environment: "node",
    include: ["atlante/test-interfaccia/**/*.test.ts"],
  },
};
