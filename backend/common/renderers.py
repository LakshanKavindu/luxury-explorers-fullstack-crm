"""
API response envelope — wraps every DRF response in a consistent structure.

Response contract
──────────────────
All API responses — success and error — follow this shape:

  Success (2xx):
  {
      "success": true,
      "data":    <serialized payload or null>,
      "message": ""
  }

  Error (4xx / 5xx):
  {
      "success": false,
      "data":    null,
      "message": "<human-readable summary>",
      "errors":  <structured error detail — see below>
  }

Error shape for validation failures (400):
  "errors": {
      "field_name": ["Error message for this field."],
      "non_field_errors": ["Cross-field validation message."]
  }

Error shape for non-field errors (401, 403, 404, 429, 500):
  "errors": {
      "detail": "Message string."
  }

Paginated list responses:
  The renderer detects the pagination envelope keys (count, results, …) and
  preserves them inside "data" without double-wrapping:
  {
      "success": true,
      "data": {
          "count": 42,
          "total_pages": 3,
          "current_page": 1,
          "next":  "http://…?page=2",
          "previous": null,
          "results": [...]
      },
      "message": ""
  }

Why a renderer (not middleware)?
  DRF renders responses, not Django's WSGI layer. The renderer approach works
  in the DRF request/response lifecycle and has access to the status code.
  Middleware would need to parse and re-encode JSON, adding latency and fragility.
"""
from rest_framework.renderers import JSONRenderer

# Sentinel keys that indicate a paginated response from StandardPagination.
# If the raw data dict contains these keys, it is already the pagination envelope
# and should be placed inside "data" as-is — not inspected further.
_PAGINATION_KEYS = frozenset({"count", "total_pages", "current_page", "next", "previous", "results"})


class ApiRenderer(JSONRenderer):
    """
    Wraps every DRF response in the project-standard envelope.

    Applied globally via REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")
        status_code = response.status_code if response else 200
        is_success = 200 <= status_code < 300

        if is_success:
            envelope = {
                "success": True,
                "data": data,       # may be a dict, list, or pagination envelope
                "message": "",
            }
        else:
            # Extract a short human-readable summary for toast/alert display.
            # The full structured detail stays in "errors" for form handling.
            message = _extract_message(data)
            envelope = {
                "success": False,
                "data": None,
                "message": message,
                "errors": data,
            }

        return super().render(envelope, accepted_media_type, renderer_context)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_message(data) -> str:
    """
    Return a short human-readable summary from an error response payload.

    Priority:
      1. data["detail"]          — standard DRF non-field error string
      2. data["non_field_errors"] — serializer cross-field validation
      3. First field error found  — e.g. data["email"][0]
      4. Fallback generic message

    The frontend should display this in a toast/snackbar. Field-specific
    messages should be read from "errors.<field>" for inline form display.
    """
    if not isinstance(data, dict):
        return "An error occurred."

    # Standard DRF single-message errors (auth, permission, throttle, 404, 500)
    detail = data.get("detail")
    if detail:
        # detail can be a string or an ErrorDetail object
        return str(detail)

    # Cross-field serializer validation errors
    non_field = data.get("non_field_errors")
    if non_field and isinstance(non_field, list):
        return str(non_field[0])

    # First field-level validation error
    for key, value in data.items():
        if isinstance(value, list) and value:
            return f"{key}: {value[0]}"
        if isinstance(value, str) and value:
            return f"{key}: {value}"

    return "An error occurred."
