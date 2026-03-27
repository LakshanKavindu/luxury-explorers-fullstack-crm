"""
Audit service — the single source of truth for creating ActivityLog records.

Signals vs service layer — decision rationale
──────────────────────────────────────────────
We use a service layer (this module) instead of Django signals for three
concrete reasons:

1. Signals don't carry request.user.
   post_save / post_delete receive the model instance, not the HTTP request.
   To get the current user you would have to store it in a thread-local
   variable (e.g. via middleware), which is fragile under async Django (ASGI),
   breaks Celery workers, and makes unit testing complicated.
   The service function receives `user` as an explicit argument — no magic.

2. Our "delete" is a soft delete (is_deleted=True → save()).
   post_delete fires only on hard ORM deletes. Our destroy() method calls
   instance.save(update_fields=["is_deleted"]) — which fires post_save,
   not post_delete. Distinguishing "was this save a deletion?" inside a
   signal requires fragile pre_save / post_save state comparison tricks.
   In the service layer we pass Action.DELETE explicitly — no guessing.

3. Signals fire for ALL saves — migrations, loaddata, admin, shell, bulk
   updates, fixtures. This would flood the audit log with system noise.
   The service is called only from the CRM ViewSets —  exactly the mutations
   that need to be audited.

Usage
──────
  from apps.audit.services import log_activity
  from apps.audit.models import ActivityLog

  # In a ViewSet perform_create / perform_update / destroy:
  log_activity(
      user=request.user,
      action=ActivityLog.Action.CREATE,
      instance=serializer.instance,
  )

The function is intentionally synchronous. If you later move to Celery,
wrap the call in a task — but keep the call site the same.
"""
from __future__ import annotations

import logging

from apps.audit.models import ActivityLog

logger = logging.getLogger(__name__)


def log_activity(
    *,
    user,
    action: str,
    instance,
) -> ActivityLog | None:
    """
    Create a single ActivityLog entry for a CRM mutation.

    Parameters
    ──────────
    user     : The authenticated User who performed the action.
               Accepts None (e.g. system/automated actions) — the FK is
               SET_NULL so the log is preserved even when the user is later
               deactivated.
    action   : One of ActivityLog.Action.CREATE / UPDATE / DELETE.
               Use the TextChoices constant, not the raw string, to prevent
               typos: ActivityLog.Action.CREATE, not "create".
    instance : The Django model instance that was mutated (Company or Contact).
               Must have .pk, .organization, and a meaningful __str__().

    Returns
    ────────
    The saved ActivityLog instance, or None if creation failed (logged
    as an error — we never let audit failures bubble up and break the
    user-facing request).

    Why keyword-only arguments (*)?
      Prevents silent argument reordering bugs. Calling code must be explicit:
        log_activity(user=u, action=a, instance=i)   ✓
        log_activity(u, a, i)                         ✗ TypeError

    Why swallow exceptions?
      An audit failure must never roll back a successful CRM mutation.
      If the ActivityLog INSERT fails (e.g. DB outage, constraint conflict),
      we log the error and allow the main response to complete normally.
      The alternative — letting it raise — would roll back the Company/Contact
      save, giving the user a 500 for what was actually a successful operation.
    """
    try:
        org = getattr(instance, "organization", None)
        if org is None:
            logger.warning(
                "log_activity: instance %s has no organization — skipping audit log.",
                instance,
            )
            return None

        entry = ActivityLog.objects.create(
            user=user if (user and user.is_authenticated) else None,
            action=action,
            organization=org,
            model_name=type(instance).__name__,      # "Company" or "Contact"
            object_id=str(instance.pk),              # UUID as string
            object_repr=str(instance)[:255],         # truncated __str__ snapshot
        )
        return entry

    except Exception:
        logger.exception(
            "log_activity: failed to create ActivityLog for %s %s (pk=%s). "
            "The original mutation was NOT rolled back.",
            action,
            type(instance).__name__,
            instance.pk,
        )
        return None
