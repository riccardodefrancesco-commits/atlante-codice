/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Plane features that Atlante hides (docs/specifica/10-funzioni-di-plane.md in zeta3-progetti).
 * Hidden, never deleted: Plane's code stays, so security fixes still apply. To show one again,
 * remove it from here (and, for the menu entries, give back the roles in
 * packages/constants/src/workspace.ts).
 */

/** Project features whose switch is hidden (cycles start off on every new project). */
export const ATLANTE_HIDDEN_PROJECT_FEATURES: readonly string[] = ["cycles"];

/** Personal entries of the side menu, also in "Customize navigation". */
export const ATLANTE_HIDDEN_PERSONAL_NAVIGATION: readonly string[] = ["stickies"];

/** Widgets of the Home, also in "Manage widgets". */
export const ATLANTE_HIDDEN_HOME_WIDGETS: readonly string[] = ["my_stickies"];

/** Commands of the command palette. */
export const ATLANTE_HIDDEN_COMMANDS: readonly string[] = [
  "nav_workspace_analytics",
  "nav_project_cycles",
  "open_project_cycle",
];

/** The Analytics button in the pages of a project's tasks and modules (the menu entry is already hidden). */
export const ATLANTE_SHOW_ANALYTICS = false;

/** Plane's links and promotion (docs, sales, forum, news, "star on GitHub", paid plans, the
 * login page's customer logos and Plane's terms): hidden in Atlante. */
export const ATLANTE_SHOW_PLANE_LINKS = false;

/** Plane's start date: every task has two dates, "Consegna" (Plane's due date) and "Pubblicazione"
 * (Atlante's), decided by Rick on 22 October (design system, table 16). The field stays, hidden. */
export const ATLANTE_SHOW_START_DATE = false;

/** Where Atlante's own source code is (AGPL-3.0: the people who use Atlante can have it). */
export const ATLANTE_SOURCE_URL = "https://github.com/riccardodefrancesco-commits/atlante-codice";
