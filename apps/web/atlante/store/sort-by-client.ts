/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { orderBy } from "lodash-es";
import type { TIssue, TIssueOrderByOptions } from "@plane/types";

type TClientOrderKey = "atlante_client__name" | "-atlante_client__name";

export const isAtlanteClientOrderKey = (key: TIssueOrderByOptions | undefined): key is TClientOrderKey =>
  key === "atlante_client__name" || key === "-atlante_client__name";

/** Orders work items by their client's name, items without client last, like the server does.
 * The items arrive already ordered by creation date, which stays as the tie-break. */
export const sortIssuesByClient = (
  issues: TIssue[],
  key: TClientOrderKey,
  getClientName: (clientId: string | null | undefined) => string | undefined
): TIssue[] => {
  const nameOf = (issue: TIssue) => getClientName(issue.atlante_client_id)?.toLocaleLowerCase("it");
  return orderBy(
    issues,
    [(issue) => (nameOf(issue) ? 0 : 1), nameOf],
    ["asc", key === "-atlante_client__name" ? "desc" : "asc"]
  );
};
