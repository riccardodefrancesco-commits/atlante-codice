/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TNotificationContentMap } from "@/components/workspace-notifications/sidebar/notification-card/content";

/** The inbox notices of the phase rules (request 11, "avviso a chi viene dopo"), written by the
 * "Atlante" automation: "Atlante ti ha dato la task nella fase In montaggio." */
export const ATLANTE_NOTIFICATION_CONTENT_MAP: TNotificationContentMap = {
  atlante_phase: ({ newValue }) => ({ action: "ti ha dato la task nella fase", value: newValue, showConnector: false }),
  atlante_to_assign: ({ newValue }) => ({
    action: "ti segnala una task da assegnare nella fase",
    value: newValue,
    showConnector: false,
  }),
};
