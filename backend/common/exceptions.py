"""
Custom DRF exception handler.
Ensures all errors (including Django 404/500) are returned in the
ApiRenderer envelope format.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Call DRF's default handler first, then reformat if needed.
    """
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exception — return a generic 500
        return Response(
            {
                "detail": "An unexpected server error occurred.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
