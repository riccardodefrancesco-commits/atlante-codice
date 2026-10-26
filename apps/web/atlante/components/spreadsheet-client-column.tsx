/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import type { TIssue } from "@plane/types";
import { AtlanteClientBadge } from "@/atlante/components/client-badge";

type Props = {
  issue: TIssue;
  onClose: () => void;
  disabled: boolean;
};

/** The "Client" cell of the table. Read only here: the client is changed from the work item (pezzo 6). */
export const SpreadsheetAtlanteClientColumn = observer(function SpreadsheetAtlanteClientColumn(props: Props) {
  const { issue } = props;
  return (
    <div className="flex h-11 items-center border-b-[0.5px] border-subtle px-2.5">
      <AtlanteClientBadge clientId={issue.atlante_client_id} projectId={issue.project_id} variant="name" />
    </div>
  );
});
