"""Patch merge helpers. Only keys present in a patch change."""

from app.domain.complaint import (
    ComplaintFieldKey,
    ComplaintFieldValue,
    ComplaintFields,
    ComplaintPatch,
)


def empty_patch() -> ComplaintPatch:
    return ComplaintPatch(changes={})


def fields_from_dump(payload: dict[str, object]) -> ComplaintFields:
    return ComplaintFields.model_validate(payload)


def fields_to_dump(fields: ComplaintFields) -> dict[str, object]:
    return fields.model_dump(mode="json")


def patch_from_dump(payload: dict[str, object] | None) -> ComplaintPatch:
    if not payload:
        return empty_patch()
    return ComplaintPatch.model_validate(payload)


def patch_to_dump(patch: ComplaintPatch) -> dict[str, object]:
    return patch.model_dump(mode="json")


def merge_fields(current: ComplaintFields, patch: ComplaintPatch) -> ComplaintFields:
    merged = current.model_copy(deep=True)
    for key, value in patch.changes.items():
        setattr(merged, key.value if isinstance(key, ComplaintFieldKey) else key, value)
    return merged


def combine_patches(*patches: ComplaintPatch) -> ComplaintPatch:
    changes: dict[ComplaintFieldKey, ComplaintFieldValue] = {}
    for patch in patches:
        for key, value in patch.changes.items():
            field_key = key if isinstance(key, ComplaintFieldKey) else ComplaintFieldKey(key)
            changes[field_key] = value
    return ComplaintPatch(changes=changes)


def patch_field_keys(patch: ComplaintPatch) -> set[ComplaintFieldKey]:
    keys: set[ComplaintFieldKey] = set()
    for key in patch.changes:
        keys.add(key if isinstance(key, ComplaintFieldKey) else ComplaintFieldKey(key))
    return keys
