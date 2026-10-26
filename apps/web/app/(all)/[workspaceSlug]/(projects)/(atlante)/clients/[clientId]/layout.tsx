/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Outlet } from "react-router";
import { AppHeader } from "@/components/core/app-header";
import { ContentWrapper } from "@/components/core/content-wrapper";
import { AtlanteClientDetailHeader } from "@/atlante/components/clients/client-detail-header";

export default function AtlanteClientDetailLayout() {
  return (
    <>
      <AppHeader header={<AtlanteClientDetailHeader />} />
      <ContentWrapper>
        <Outlet />
      </ContentWrapper>
    </>
  );
}
