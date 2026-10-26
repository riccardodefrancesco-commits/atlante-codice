/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { format } from "date-fns";
import type { Locale } from "date-fns";

/** The default trigger label format — a short, unambiguous day. Overridden by `formatToken`. */
export const DEFAULT_DATE_FORMAT_TOKEN = "MMM dd, yyyy";

// ATLANTE: the app sets once the default label format and language of the date pickers (Atlante:
// "d MMM yyyy" in Italian, apps/web/atlante/setup.ts). Unset, they stay Plane's, and so do its tests.
let dateSelectDefaults: { formatToken: string; locale?: Locale } = { formatToken: DEFAULT_DATE_FORMAT_TOKEN };
export const setDateSelectDefaults = (next: { formatToken?: string; locale?: Locale }) => {
  dateSelectDefaults = { ...dateSelectDefaults, ...next };
};
export const getDateSelectDefaults = () => dateSelectDefaults;
/** ATLANTE: date-fns format in the app's language. */
export const formatInAppLanguage = (date: Date, token: string) =>
  format(date, token, { locale: dateSelectDefaults.locale });

/**
 * Turns a `minDate` / `maxDate` pair into propel `Calendar` day matchers. Both bounds are
 * inclusive, so they become "before min" / "after max" exclusions rather than the bounds
 * themselves. Typed structurally — react-day-picker's `Matcher` reaches this package only through
 * propel, so it is not imported here.
 */
export function buildDisabledMatchers(
  minDate?: Date,
  maxDate?: Date
): ({ before: Date } | { after: Date })[] | undefined {
  if (!minDate && !maxDate) return undefined;
  const matchers: ({ before: Date } | { after: Date })[] = [];
  if (minDate) matchers.push({ before: minDate });
  if (maxDate) matchers.push({ after: maxDate });
  return matchers;
}
