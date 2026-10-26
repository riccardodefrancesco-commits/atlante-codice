/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { personName } from "@/atlante/person-name";

describe("nome delle persone nelle schermate dei clienti (zeta3-progetti#21)", () => {
  it("usa nome e cognome", () => {
    expect(personName({ first_name: "Bruno", last_name: "Prova", display_name: "bruno" })).toBe("Bruno Prova");
  });
  it("usa il nome visualizzato solo se nome e cognome mancano", () => {
    expect(personName({ first_name: "", last_name: null, display_name: "bruno" })).toBe("bruno");
    expect(personName({ first_name: "Anna", last_name: "", display_name: "anna" })).toBe("Anna");
  });
  it("non mostra niente se la persona manca", () => {
    expect(personName(undefined)).toBe("");
  });
});
