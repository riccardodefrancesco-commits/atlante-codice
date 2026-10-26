/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { isAtlanteClientOrderKey, sortIssuesByClient } from "@/atlante/store/sort-by-client";

const names = { a: "Alfa Biscotti", b: "beta Moda", g: "Gamma Palestre" };
const issues = [
  { id: "1", atlante_client_id: "g" },
  { id: "2", atlante_client_id: null },
  { id: "3", atlante_client_id: "a" },
  { id: "4", atlante_client_id: "b" },
  { id: "5", atlante_client_id: "a" },
];
const nameOf = (id) => (id ? names[id] : undefined);

describe("ordering by client", () => {
  it("knows its two keys only", () => {
    expect(isAtlanteClientOrderKey("atlante_client__name")).toBe(true);
    expect(isAtlanteClientOrderKey("-atlante_client__name")).toBe(true);
    expect(isAtlanteClientOrderKey("-created_at")).toBe(false);
  });

  it("orders A to Z ignoring capitals, keeps the given order inside a client, items without client last", () => {
    const ids = sortIssuesByClient(issues, "atlante_client__name", nameOf).map((issue) => issue.id);
    expect(ids).toEqual(["3", "5", "4", "1", "2"]);
  });

  it("orders Z to A, items without client still last", () => {
    const ids = sortIssuesByClient(issues, "-atlante_client__name", nameOf).map((issue) => issue.id);
    expect(ids).toEqual(["1", "4", "3", "5", "2"]);
  });
});
