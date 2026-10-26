/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { projectCodeFromName } from "@/atlante/project-code";
import { AtlanteProjectService } from "@/atlante/services/project.service";

const projectService = new AtlanteProjectService();
// Ask the server only when the person stops typing for a moment.
const WAIT_MS = 250;

/**
 * While the name of a new project is typed, proposes its code (zeta3-progetti#18). onCode gets the
 * code only while `enabled` is true: once the person writes the code by hand, Atlante stops proposing.
 */
export function useAtlanteProjectCode(onCode: (code: string) => void, enabled: boolean) {
  const { workspaceSlug } = useParams();
  const enabledRef = useRef(enabled);
  const onCodeRef = useRef(onCode);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const lastRequest = useRef(0);
  enabledRef.current = enabled;
  onCodeRef.current = onCode;

  useEffect(() => () => clearTimeout(timer.current), []);

  return useCallback(
    (name: string) => {
      clearTimeout(timer.current);
      const request = ++lastRequest.current;
      const answer = (code: string) => {
        // Only the answer to the last name typed counts, and only while the code is not typed by hand.
        if (request === lastRequest.current && enabledRef.current) onCodeRef.current(code);
      };
      timer.current = setTimeout(() => {
        if (!workspaceSlug) return answer(projectCodeFromName(name));
        projectService
          .getProjectCode(workspaceSlug.toString(), name)
          .then(answer)
          .catch(() => answer(projectCodeFromName(name)));
      }, WAIT_MS);
    },
    [workspaceSlug]
  );
}
