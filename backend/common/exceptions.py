"""
Custom DRF exception handler.

Ensures every error response — including unhandled Django exceptions —
is returned in the ApiRenderer envelope format.

Why a custom handler?
──────────────────────
DRF's default exception_handler only processes exceptions that are subclasses
of rest_framework.exceptions.APIException. Anything else (e.g. an unhandled
Python exception, a Django Http404, a PermissionDenied from Django's own layer)
returns None, which DRF converts to a bare 500. This handler catches all of
those and normalises them into the project-standard structure.

Exception → HTTP status mapping
─────────────────────────────────
  ValidationError             → 400  (field errors or non_field_errors)
  AuthenticationFailed        → 401
  NotAuthenticated            → 401
  PermissionDenied (DRF)      → 403
  django.core.exceptions.PermissionDenied → 403
  NotFound                    → 404
  django.http.Http404         → 404
  MethodNotAllowed            → 405
  Throttled                   → 429
  All other APIExceptions     → exception.status_code
  Everything else             → 500

Response structure guaranteed for all cases:
  {
      "success": false,
      "data":    null,
      "message": "<short human-readable summary>",
      "errors": {
          "detail": "<same summary>"          ← for non-field errors
          -- OR --
          "<field>": ["<message>", ...]       ← for 400 ValidationError
      }
  }

Settings wire-up (already configured in base.py):
  REST_FRAMEWORK = {
      "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
  }
"""
from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404

from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context) -> Response:
    """
    Central exception handler for all DRF views.

    Processing order:
      1. Convert Django-native exceptions to DRF equivalents so DRF's default
         handler can process them (Http404 → NotFound, PermissionDenied → 403).
      2. Call DRF's default handler — it normalises APIExceptions into Responses.
      3. If DRF returned None (truly unhandled), return a safe generic 500.
      4. Normalise the response body into the project envelope via _build_error_response().
    """
    # ── Step 1: Convert Django exceptions that DRF doesn't handle natively ────
    if isinstance(exc, Http404):
        exc = NotFound(detail="The requested resource was not found.")
    elif isinstance(exc, DjangoPermissionDenied):
        exc = PermissionDenied(detail="You do not have permission to perform this action.")

    # ── Step 2: Let DRF process the (now normalised) exception ────────────────
    response = exception_handler(exc, context)

    # ── Step 3: Unhandled exception → safe generic 500 ───────────────────────
    if response is None:
        # Log the full traceback so it appears in server logs / Sentry
        logger.exception(
            "Unhandled exception in view %s",
            context.get("view", "unknown"),
            exc_info=exc,
        )
        return _build_error_response(
            detail="An unexpected server error occurred.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # ── Step 4: Normalise into project envelope ───────────────────────────────
    return _normalise_response(exc, response)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_response(exc: APIException, response: Response) -> Response:
    """
    Rewrite the response body into the project-standard error shape.

    DRF's default handler produces either:
      {"detail": "..."}                for most errors
      {"field": ["...", ...], ...}     for ValidationError (400)

    We pass these through to "errors" unchanged and extract a short summary
    into "message" for toast display.

    We do NOT wrap the data here — ApiRenderer does the envelope wrapping.
    The exception handler's job is only to ensure the right *content* is in
    the response before the renderer sees it.
    """
    data = response.data

    # ValidationError shapes can be either:
    #   {"field": ["msg"]}   — field errors
    #   {"non_field_errors": ["msg"]}   — cross-field errors
    #   {"detail": "msg"}    — simple message (rare for ValidationError)
    # We leave the structure intact for the frontend to do field-level display.
    # The renderer's _extract_message() will pick the summary from whichever
    # key is present.

    if isinstance(exc, ValidationError):
        # Body is already the correct shape — field errors keyed by field name.
        # Don't wrap it further.
        response.data = data
        return response

    # For all other exceptions, normalise to {"detail": "<message>"}
    # so the renderer always has a consistent key to extract the summary from.
    if isinstance(data, dict) and "detail" in data:
        # Already in the right shape — pass through
        pass
    elif isinstance(data, list):
        # Rare edge case: DRF returns a list (e.g. nested serializer errors)
        response.data = {"detail": str(data[0]) if data else "An error occurred."}
    else:
        response.data = {"detail": str(data)}

    return response


def _build_error_response(detail: str, status_code: int) -> Response:
    """
    Build a minimal error Response without going through DRF's exception flow.
    Used for unhandled 500s where response is None from DRF's handler.

    The renderer will wrap this in the envelope; we only set the body content.
    """
    return Response(
        {"detail": detail},
        status=status_code,
    )
