/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TCalendarLayouts } from "@plane/types";
import { EStartOfTheWeek } from "@plane/types";

export const MONTHS_LIST: {
  [monthNumber: number]: {
    shortTitle: string;
    title: string;
  };
} = {
  1: {
    shortTitle: "Gen", // ATLANTE: in italiano
    title: "Gennaio",
  },
  2: {
    shortTitle: "Feb", // ATLANTE: in italiano
    title: "Febbraio",
  },
  3: {
    shortTitle: "Mar", // ATLANTE: in italiano
    title: "Marzo",
  },
  4: {
    shortTitle: "Apr", // ATLANTE: in italiano
    title: "Aprile",
  },
  5: {
    shortTitle: "Mag", // ATLANTE: in italiano
    title: "Maggio",
  },
  6: {
    shortTitle: "Giu", // ATLANTE: in italiano
    title: "Giugno",
  },
  7: {
    shortTitle: "Lug", // ATLANTE: in italiano
    title: "Luglio",
  },
  8: {
    shortTitle: "Ago", // ATLANTE: in italiano
    title: "Agosto",
  },
  9: {
    shortTitle: "Set", // ATLANTE: in italiano
    title: "Settembre",
  },
  10: {
    shortTitle: "Ott", // ATLANTE: in italiano
    title: "Ottobre",
  },
  11: {
    shortTitle: "Nov", // ATLANTE: in italiano
    title: "Novembre",
  },
  12: {
    shortTitle: "Dic", // ATLANTE: in italiano
    title: "Dicembre",
  },
};

export const DAYS_LIST: {
  [dayIndex: number]: {
    shortTitle: string;
    title: string;
    value: EStartOfTheWeek;
  };
} = {
  1: {
    shortTitle: "Dom", // ATLANTE: in italiano
    title: "Domenica",
    value: EStartOfTheWeek.SUNDAY,
  },
  2: {
    shortTitle: "Lun", // ATLANTE: in italiano
    title: "Lunedì",
    value: EStartOfTheWeek.MONDAY,
  },
  3: {
    shortTitle: "Mar", // ATLANTE: in italiano
    title: "Martedì",
    value: EStartOfTheWeek.TUESDAY,
  },
  4: {
    shortTitle: "Mer", // ATLANTE: in italiano
    title: "Mercoledì",
    value: EStartOfTheWeek.WEDNESDAY,
  },
  5: {
    shortTitle: "Gio", // ATLANTE: in italiano
    title: "Giovedì",
    value: EStartOfTheWeek.THURSDAY,
  },
  6: {
    shortTitle: "Ven", // ATLANTE: in italiano
    title: "Venerdì",
    value: EStartOfTheWeek.FRIDAY,
  },
  7: {
    shortTitle: "Sab", // ATLANTE: in italiano
    title: "Sabato",
    value: EStartOfTheWeek.SATURDAY,
  },
};

export const CALENDAR_LAYOUTS: {
  [layout in TCalendarLayouts]: {
    key: TCalendarLayouts;
    title: string;
  };
} = {
  month: {
    key: "month",
    title: "Vista mese" /* ATLANTE: in italiano */,
  },
  week: {
    key: "week",
    title: "Vista settimana" /* ATLANTE: in italiano */,
  },
};
