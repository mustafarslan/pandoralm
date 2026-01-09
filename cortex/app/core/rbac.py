"""
RBAC (Role-Based Access Control) Decorators
Protect endpoints based on user roles
"""
from functools import wraps
from typing import Callable, List, Optional
from fastapi import HTTPException, Depends

from app.core.security import UserContext, require_auth


class RBACError(HTTPException):
    """RBAC authorization error."""
    def __init__(self, detail: str):
        super().__init__(status_code=403, detail=detail)


def check_permission(
    user: UserContext,
    required_roles: List[str] = None,
    required_groups: List[str] = None,
    any_of: bool = True,
) -> bool:
    """
    Check if user has required permissions.

    Args:
        user: Authenticated user context
        required_roles: List of required roles
        required_groups: List of required groups
        any_of: If True, requires ANY role/group. If False, requires ALL.

    Returns:
        True if authorized
    """
    if not required_roles and not required_groups:
        return True

    role_check = True
    group_check = True

    if required_roles:
        if any_of:
            role_check = user.has_any_role(required_roles)
        else:
            role_check = user.has_all_roles(required_roles)

    if required_groups:
        user_groups_lower = [g.lower() for g in user.groups]
        if any_of:
            group_check = any(g.lower() in user_groups_lower for g in required_groups)
        else:
            group_check = all(g.lower() in user_groups_lower for g in required_groups)

    if any_of:
        return role_check or group_check
    else:
        return role_check and group_check


class Permission:
    """
    Permission requirement for endpoint protection.

    Usage:
        @router.get("/admin", dependencies=[Depends(Permission.admin())])
        @router.get("/vectors", dependencies=[Depends(Permission.vector_ops())])
    """

    @staticmethod
    def admin():
        """Require admin role."""
        async def check(user: UserContext = Depends(require_auth)) -> UserContext:
            if not user.is_admin():
                raise RBACError("Admin access required")
            return user
        return check

    @staticmethod
    def vector_ops():
        """Require vector-ops or admin role."""
        async def check(user: UserContext = Depends(require_auth)) -> UserContext:
            if not user.is_vector_ops():
                raise RBACError("Vector operations access required")
            return user
        return check

    @staticmethod
    def roles(*required_roles: str, any_of: bool = True):
        """Require specific roles."""
        async def check(user: UserContext = Depends(require_auth)) -> UserContext:
            if not check_permission(user, required_roles=list(required_roles), any_of=any_of):
                raise RBACError(f"Required roles: {', '.join(required_roles)}")
            return user
        return check

    @staticmethod
    def groups(*required_groups: str, any_of: bool = True):
        """Require membership in specific groups."""
        async def check(user: UserContext = Depends(require_auth)) -> UserContext:
            if not check_permission(user, required_groups=list(required_groups), any_of=any_of):
                raise RBACError(f"Required groups: {', '.join(required_groups)}")
            return user
        return check

    @staticmethod
    def workspace_member(workspace_id_param: str = "workspace_id"):
        """
        Require user to be a member of the workspace.

        Checks if user's groups include the workspace.
        """
        async def check(
            user: UserContext = Depends(require_auth),
            # Workspace ID would come from path parameter
        ) -> UserContext:
            # TODO: Implement workspace membership check
            # For now, allow all authenticated users
            return user
        return check


# Convenience aliases
require_admin = Permission.admin
require_vector_ops = Permission.vector_ops
