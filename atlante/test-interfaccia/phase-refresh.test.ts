/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// After a phase change the server picked executors and deadline: the screen reads them back.
vi.mock("@/services/issue/issue.service", () => ({
  IssueService: class {
    retrieve = async () => ({
      id: "t1",
      assignee_ids: ["elena"],
      target_date: "2026-10-23",
      state_id: "montaggio",
      name: "Reel",
    });
  },
}));

import { approvalKey, refreshAfterPhaseChange, taskChoicesKey } from "@/atlante/store/phase-refresh";

const fakeRoot = () => {
  const issues: Record<string, Record<string, unknown>> = {
    t1: { id: "t1", assignee_ids: ["dario"], target_date: "2026-10-30", name: "Reel" },
  };
  const calls: unknown[] = [];
  return {
    issues,
    calls,
    root: {
      issues: {
        getIssueById: (id: string) => issues[id],
        updateIssue: (id: string, data: Record<string, unknown>) => {
          issues[id] = { ...issues[id], ...data };
        },
      },
      issueDetail: {
        activity: { fetchActivities: async (...args: string[]) => calls.push(["history", ...args]) },
      },
    },
  };
};

describe("dopo il cambio di fase", () => {
  it("mostra subito esecutori e scadenza scelti dalla regola, e la riga nello storico", async () => {
    const { root, issues, calls } = fakeRoot();
    const moved: unknown[] = [];
    const reloaded: string[] = [];
    await refreshAfterPhaseChange(root as never, "zeta3-prova", "p1", "t1", {
      updateIssueList: (after, before) => moved.push([before?.assignee_ids, after?.assignee_ids]),
      revalidate: (key) => reloaded.push(key),
    });
    expect(issues.t1).toMatchObject({
      assignee_ids: ["elena"],
      target_date: "2026-10-23",
      state_id: "montaggio",
      name: "Reel",
    });
    // The task moves to its new group in a list grouped by executor.
    expect(moved).toEqual([[["dario"], ["elena"]]]);
    expect(calls).toEqual([["history", "zeta3-prova", "p1", "t1"]]);
    // The rows of the task (responsible person, roles, phase rule) and the client's approval are read again.
    expect(reloaded).toEqual([taskChoicesKey("t1"), approvalKey("t1")]);
  });
});
