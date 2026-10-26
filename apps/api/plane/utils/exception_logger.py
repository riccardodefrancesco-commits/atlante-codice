# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import logging
import traceback

# Django imports
from django.conf import settings

from plane.atlante.error_codes import log_fields, new_code  # ATLANTE: a code for every error


def log_exception(e, warning=False):
    # Log the error
    logger = logging.getLogger("plane.exception")
    # ATLANTE: every logged error gets a short code, returned to the caller and written in the log
    # with page, action and the person's id (plane/atlante/error_codes.py)
    code = new_code()
    fields = log_fields(code)

    if warning:
        logger.warning(str(e), extra=fields)
    else:
        logger.exception(e, extra=fields)

    if settings.DEBUG:
        logger.debug(traceback.format_exc())
    return code  # ATLANTE
