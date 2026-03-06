from typing import Optional
from sage_is_ai.models.groups import Groups


def get_facilitator_scope(user_id: str) -> dict:
    """Returns the scope of a facilitator: their managed groups, which have admins, and managed user IDs."""
    groups = Groups.get_groups_where_facilitator(user_id)
    managed_group_ids = [g.id for g in groups]
    groups_with_admin = [g.id for g in groups if Groups.has_admin_in_group(g.id)]

    managed_user_ids = set()
    for g in groups:
        if g.user_ids:
            managed_user_ids.update(g.user_ids)

    return {
        "groups": groups,
        "managed_group_ids": managed_group_ids,
        "groups_with_admin": groups_with_admin,
        "managed_user_ids": list(managed_user_ids),
    }


def can_facilitator_manage_group(user_id: str, group_id: str) -> bool:
    """Check if a facilitator can manage a specific group."""
    return Groups.is_facilitator_of_group(user_id, group_id)


def can_facilitator_manage_user(facilitator_id: str, target_user_id: str) -> bool:
    """Check if a facilitator can manage a target user (target must be in facilitator's groups)."""
    scope = get_facilitator_scope(facilitator_id)
    return target_user_id in scope["managed_user_ids"]


def can_facilitator_change_permissions(facilitator_id: str, group_id: str) -> bool:
    """Facilitator can only change permissions if no admin is in the group."""
    if not can_facilitator_manage_group(facilitator_id, group_id):
        return False
    return not Groups.has_admin_in_group(group_id)
