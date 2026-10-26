/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { PageHead } from "@/components/core/page-title";
import { AtlanteClientDetail } from "@/atlante/components/clients/client-detail";
import { useAtlanteClient } from "@/atlante/hooks/use-atlante-client";
import type { Route } from "./+types/page";

function AtlanteClientDetailPage({ params }: Route.ComponentProps) {
  const { t } = useTranslation();
  const { getClientById } = useAtlanteClient();
  const client = getClientById(params.clientId);
  return (
    <>
      <PageHead title={client?.name ?? t("atlante.client.label")} />
      <AtlanteClientDetail workspaceSlug={params.workspaceSlug} clientId={params.clientId} />
    </>
  );
}

export default observer(AtlanteClientDetailPage);
