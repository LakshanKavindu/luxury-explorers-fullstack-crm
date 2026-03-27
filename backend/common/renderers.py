"""
Custom API renderer — wraps all DRF responses in a consistent envelope:

Success:
    { "success": true, "data": {...}, "message": "" }

Error:
    { "success": false, "data": null, "errors": {...}, "message": "..." }
"""
from rest_framework.renderers import JSONRenderer
import json


class ApiRenderer(JSONRenderer):
    """Uniform JSON response envelope for all API endpoints."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None
        status_code = response.status_code if response else 200

        is_success = 200 <= status_code < 300

        if is_success:
            envelope = {
                "success": True,
                "data": data,
                "message": "",
            }
        else:
            # Flatten error detail into a readable message
            message = ""
            if isinstance(data, dict):
                detail = data.get("detail", "")
                message = str(detail) if detail else ""
            envelope = {
                "success": False,
                "data": None,
                "errors": data,
                "message": message,
            }

        return super().render(envelope, accepted_media_type, renderer_context)
