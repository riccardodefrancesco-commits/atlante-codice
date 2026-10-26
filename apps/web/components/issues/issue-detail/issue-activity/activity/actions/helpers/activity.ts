/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TIssueActivity } from "@plane/types";

export const getRelationActivityContent = (activity: TIssueActivity | undefined): string | undefined => {
  if (!activity) return;

  switch (activity.field) {
    case "blocking":
      return activity.old_value === ""
        ? `ha segnato che questa task blocca la task ` // ATLANTE: storico in italiano
        : `ha tolto il blocco sulla task `;
    case "blocked_by":
      return activity.old_value === ""
        ? `ha segnato che questa task è bloccata da ` // ATLANTE
        : `ha tolto il blocco da parte della task `;
    case "duplicate":
      return activity.old_value === ""
        ? `ha segnato questa task come doppione di ` // ATLANTE
        : `ha tolto questa task come doppione di `;
    case "relates_to":
      return activity.old_value === "" ? `ha collegato questa task a ` : `ha tolto il collegamento con `; // ATLANTE
  }

  return;
};
