from .models import AuditLog


def _branch_for(instance):
    branch = getattr(instance, "branch", None)
    if branch is not None:
        return branch
    work_order = getattr(instance, "work_order", None)
    if work_order is not None:
        return work_order.branch
    invoice = getattr(instance, "invoice", None)
    if invoice is not None:
        return invoice.work_order.branch
    stock = getattr(instance, "stock", None)
    if stock is not None:
        return stock.branch
    return None


def record_audit(
    actor,
    action,
    instance,
    changed_fields=None,
    details=None,
    object_id=None,
    object_repr=None,
    branch=None,
):
    safe_details = dict(details or {})
    if changed_fields:
        safe_details["changed_fields"] = sorted(set(changed_fields))
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        branch=branch if branch is not None else _branch_for(instance),
        action=action,
        object_type=instance._meta.label_lower,
        object_id=str(object_id if object_id is not None else instance.pk or ""),
        object_repr=str(object_repr if object_repr is not None else instance)[:255],
        details=safe_details,
    )
