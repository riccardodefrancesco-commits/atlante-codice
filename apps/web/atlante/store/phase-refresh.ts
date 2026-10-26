/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { clone } from "lodash-es";
import { runInAction } from "mobx";
import { mutate } from "swr";
import type { TIssue } from "@plane/types";
import { IssueService } from "@/services/issue/issue.service";

/** The parts of Plane's issue root store this needs (store/issue/root.store.ts). */
type TRootIssueStore = {
  issues: {
    getIssueById: (issueId: string) => TIssue | undefined;
    updateIssue: (issueId: string, data: Partial<TIssue>) => void;
  };
  issueDetail: {
    activity: { fetchActivities: (workspaceSlug: string, projectId: string, issueId: string) => Promise<unknown> };
  };
};

type TRefreshOptions = {
  /** Moves the task to its new group in the list on screen (grouped by executor, for example). */
  updateIssueList?: (issue?: TIssue, issueBeforeUpdate?: TIssue) => void;
  /** Reloads a cached answer of the server (SWR's mutate); replaceable in tests. */
  revalidate?: (key: string) => unknown;
};

const issueService = new IssueService();

export const taskChoicesKey = (issueId: string) => `ATLANTE_TASK_CHOICES_${issueId}`;
export const approvalKey = (issueId: string) => `ATLANTE_APPROVAL_${issueId}`;

/** After a task enters another phase, or a choice the phase uses changes, the server may have
 * changed executors and deadline (the phase rule). They are read back so that the card, the list
 * groups and the task page show them at once, with the line in the history. */
export async function refreshAfterPhaseChange(
  root: TRootIssueStore,
  workspaceSlug: string,
  projectId: string,
  issueId: string,
  { updateIssueList, revalidate = mutate }: TRefreshOptions = {}
) {
  const fresh = await issueService.retrieve(workspaceSlug, projectId, issueId);
  runInAction(() => {
    const before = clone(root.issues.getIssueById(issueId));
    // The state too: an answer of the client moves the task to another phase on the server.
    root.issues.updateIssue(issueId, {
      assignee_ids: fresh.assignee_ids,
      target_date: fresh.target_date,
      state_id: fresh.state_id,
    });
    const after = root.issues.getIssueById(issueId);
    if (updateIssueList && before && after) updateIssueList(after, before);
  });
  void revalidate(taskChoicesKey(issueId));
  // A new phase may send the work to the client, or close what was waiting.
  void revalidate(approvalKey(issueId));
  void root.issueDetail.activity.fetchActivities(workspaceSlug, projectId, issueId);
}
