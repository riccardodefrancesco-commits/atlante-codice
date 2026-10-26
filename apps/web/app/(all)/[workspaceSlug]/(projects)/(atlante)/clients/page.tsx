/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { PageHead } from "@/components/core/page-title";
import { AtlanteClientsList } from "@/atlante/components/clients/clients-list";
import type { Route } from "./+types/page";

export default function AtlanteClientsPage({ params }: Route.ComponentProps) {
  const { t } = useTranslation();
  return (
    <>
      <PageHead title={t("atlante.client.plural")} />
      <div className="relative h-full w-full overflow-hidden overflow-y-auto">
        <AtlanteClientsList workspaceSlug={params.workspaceSlug} />
      </div>
    </>
  );
}
