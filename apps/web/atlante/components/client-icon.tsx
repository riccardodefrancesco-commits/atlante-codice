/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { FC } from "react";
import { Briefcase } from "lucide-react";
import type { ISvgIcons } from "@plane/blocks/icons";

/** The icon of "Client" in menus, filters and table headers. */
export const AtlanteClientIcon: FC<ISvgIcons> = ({ className }) => (
  <Briefcase className={className} strokeWidth={1.75} />
);
