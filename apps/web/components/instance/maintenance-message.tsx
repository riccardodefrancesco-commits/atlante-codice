/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { ATLANTE_SHOW_PLANE_LINKS } from "@/atlante/hidden-features"; // ATLANTE

export function MaintenanceMessage() {
  // ATLANTE: no link to Plane's support
  const linkMap = ATLANTE_SHOW_PLANE_LINKS
    ? [
        {
          key: "mail_to",
          label: "Contact Support",
          value: "mailto:support@plane.so",
        },
      ]
    : [];

  return (
    <>
      <div className="flex flex-col gap-2.5">
        <h1 className="text-left text-18 font-semibold text-primary">
          {/* ATLANTE: in italiano */}
          &#x1F6A7; Atlante non è partito del tutto.
        </h1>
        <span className="text-left text-14 font-medium text-secondary">
          Alcuni pezzi del programma non si sono accesi. Riprova tra qualche minuto; se la pagina resta questa, avvisa
          chi gestisce Atlante: con la diagnosi (atlante/script/diagnosi.sh) trova subito cosa non va.
        </span>
      </div>
      <div className="mt-1 flex items-center justify-start gap-6">
        {linkMap.map((link) => (
          <div key={link.key}>
            <a
              href={link.value}
              target="_blank"
              rel="noopener noreferrer"
              className="text-13 text-accent-primary hover:underline"
            >
              {link.label}
            </a>
          </div>
        ))}
      </div>
    </>
  );
}
