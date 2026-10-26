/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// The real service talks to the server: here a fake one answers.
vi.mock("@/atlante/services/client.service", () => ({
  AtlanteClientService: class {
    readonly isFake = true;
  },
}));

import { AtlanteClientStore } from "@/atlante/store/client.store";

const client = (id, name, extra = {}) => ({
  id,
  name,
  code: name.slice(0, 3).toUpperCase(),
  color: "#3E63DD",
  internal_contact: null,
  email: "",
  website: "",
  internal_notes: "",
  archived_at: null,
  created_at: "2026-10-20T10:00:00Z",
  updated_at: "2026-10-20T10:00:00Z",
  ...extra,
});

const makeStore = (service) => {
  const store = new AtlanteClientStore(service);
  store.clientMap = {
    alfa: client("alfa", "Alfa Biscotti", { project_count: 2, open_issues: 5, overdue_issues: 1 }),
    beta: client("beta", "beta Moda"),
    gamma: client("gamma", "Gamma Palestre", { archived_at: "2026-10-01T10:00:00Z" }),
  };
  store.projectClientMap = { p1: "alfa", p2: "alfa", p3: "beta" };
  return store;
};

const refused = () => Promise.reject({ name: ["Esiste già un cliente con questo nome."] });

describe("clients in memory", () => {
  it("lists active and archived clients by name, ignoring capitals", () => {
    const store = makeStore({});
    expect(store.activeClients.map((c) => c.id)).toEqual(["alfa", "beta"]);
    expect(store.archivedClients.map((c) => c.id)).toEqual(["gamma"]);
    expect(store.getClientProjectIds("alfa")).toEqual(["p1", "p2"]);
  });

  it("adds a new client with zero numbers", async () => {
    const store = makeStore({ createClient: async () => client("delta", "Delta Vini") });
    const created = await store.createClient("zeta3", { name: "Delta Vini" });
    expect(created.project_count).toBe(0);
    expect(store.getClientById("delta")?.name).toBe("Delta Vini");
  });

  it("shows a change at once and keeps the numbers the server does not send", async () => {
    let seenDuringSave;
    const store = makeStore({
      updateClient: async (_slug, id, data) => {
        seenDuringSave = store.getClientById(id)?.name;
        return client(id, data.name);
      },
    });
    await store.updateClient("zeta3", "alfa", { name: "Alfa Dolci" });
    expect(seenDuringSave).toBe("Alfa Dolci");
    expect(store.getClientById("alfa")).toMatchObject({ name: "Alfa Dolci", project_count: 2, open_issues: 5 });
  });

  it("goes back as it was when the server refuses a change", async () => {
    const store = makeStore({ updateClient: refused });
    await expect(store.updateClient("zeta3", "alfa", { name: "Beta Moda" })).rejects.toEqual({
      name: ["Esiste già un cliente con questo nome."],
    });
    expect(store.getClientById("alfa")?.name).toBe("Alfa Biscotti");
  });

  it("archives and restores, going back on error", async () => {
    const store = makeStore({
      archiveClient: async (_slug, id) => client(id, "Alfa Biscotti", { archived_at: "2026-10-20T11:00:00Z" }),
      restoreClient: refused,
    });
    await store.archiveClient("zeta3", "alfa");
    expect(store.getClientById("alfa")?.archived_at).toBe("2026-10-20T11:00:00Z");
    expect(store.activeClients.map((c) => c.id)).toEqual(["beta"]);

    await expect(store.restoreClient("zeta3", "alfa")).rejects.toBeTruthy();
    expect(store.getClientById("alfa")?.archived_at).toBe("2026-10-20T11:00:00Z");
  });

  it("links and unlinks projects, going back on error", async () => {
    const store = makeStore({ setProjectClient: async () => ({}) });
    await store.setProjectClient("zeta3", "p4", "beta");
    expect(store.getProjectClientId("p4")).toBe("beta");
    await store.setProjectClient("zeta3", "p1", null);
    expect(store.getProjectClientId("p1")).toBeUndefined();

    store.clientService = { setProjectClient: refused };
    await expect(store.setProjectClient("zeta3", "p2", "beta")).rejects.toBeTruthy();
    expect(store.getProjectClientId("p2")).toBe("alfa");
    await expect(store.setProjectClient("zeta3", "p3", null)).rejects.toBeTruthy();
    expect(store.getProjectClientId("p3")).toBe("beta");
  });
});
