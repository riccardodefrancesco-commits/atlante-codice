/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Only the pure parts are tested here: the modules that talk to Plane's stores are replaced.
vi.mock("@/hooks/use-issue-layout-store", () => ({ useIssuesStore: () => ({}) }));
vi.mock("@/lib/store-context", () => ({ StoreContext: {} }));
vi.mock("@/atlante/services/client.service", () => ({
  AtlanteClientService: class {
    readonly isFake = true;
  },
}));
vi.mock("react", () => ({
  useContext: () => undefined,
  createContext: () => ({ Provider: null }),
  useState: () => [],
}));
vi.mock("swr", () => ({ default: () => ({}), mutate: () => Promise.resolve() }));

import { moveIssueToClient } from "@/atlante/hooks/use-issue-client";

const fakeList = (loaded = true) => {
  const calls = [];
  return {
    calls,
    groupedIssueIds: loaded ? { alfa: ["i1"] } : undefined,
    removeIssueFromList: (id) => calls.push(["remove", id]),
    addIssueToList: (id) => calls.push(["add", id]),
  };
};

describe("changing the client of a work item on screen", () => {
  it("takes the item out of its group, changes the client, puts it in the new group", () => {
    const list = fakeList();
    const updateIssue = (id, data) => list.calls.push(["update", id, data.atlante_client_id]);
    moveIssueToClient(list, updateIssue, "i1", "beta");
    expect(list.calls).toEqual([
      ["remove", "i1"],
      ["update", "i1", "beta"],
      ["add", "i1"],
    ]);
  });

  it("only changes the item when the list on screen is not loaded or has no groups", () => {
    for (const store of [fakeList(false), { groupedIssueIds: {} }, undefined]) {
      const calls = [];
      moveIssueToClient(store, (id, data) => calls.push(["update", id, data.atlante_client_id]), "i1", null);
      expect(calls).toEqual([["update", "i1", null]]);
    }
  });
});
