/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// components
import type { TPowerKCommandConfig } from "@/components/power-k/core/types";
// local imports
import type { TPowerKNavigationCommandKeys } from "./commands";
import { usePowerKNavigationCommandsRecord } from "./commands";
import { useAtlanteNavigationCommands } from "@/atlante/components/power-k-commands"; // ATLANTE
import { ATLANTE_HIDDEN_COMMANDS } from "@/atlante/hidden-features"; // ATLANTE

export const usePowerKNavigationCommands = (): TPowerKCommandConfig[] => {
  const optionsList: Record<TPowerKNavigationCommandKeys, TPowerKCommandConfig> = usePowerKNavigationCommandsRecord();
  const atlanteCommands = useAtlanteNavigationCommands(); // ATLANTE: "Go to Clients"

  return [
    // Open actions from lowest to highest scope
    optionsList["open_project_cycle"],
    optionsList["open_project_module"],
    optionsList["open_project_view"],
    optionsList["open_project_setting"],
    optionsList["open_project"],
    optionsList["open_workspace_setting"],
    optionsList["open_workspace"],
    // User-Level Navigation
    optionsList["nav_home"],
    optionsList["nav_inbox"],
    optionsList["nav_your_work"],
    // Project-Level Navigation (Only visible in project context)
    optionsList["nav_project_work_items"],
    optionsList["nav_project_pages"],
    optionsList["nav_project_cycles"],
    optionsList["nav_project_modules"],
    optionsList["nav_project_views"],
    optionsList["nav_project_intake"],
    optionsList["nav_project_settings"],
    optionsList["nav_project_archives"],
    // Navigate to workspace-level pages
    optionsList["nav_all_workspace_work_items"],
    optionsList["nav_assigned_workspace_work_items"],
    optionsList["nav_created_workspace_work_items"],
    optionsList["nav_subscribed_workspace_work_items"],
    optionsList["nav_workspace_analytics"],
    optionsList["nav_workspace_settings"],
    optionsList["nav_workspace_drafts"],
    optionsList["nav_workspace_archives"],
    optionsList["nav_projects_list"],
    ...atlanteCommands, // ATLANTE
    // Account-Level Navigation
    optionsList["nav_account_settings"],
  ].filter((command) => !ATLANTE_HIDDEN_COMMANDS.includes(command.id)); // ATLANTE: hidden features
};
