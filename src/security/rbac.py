"""
Role-Based Access Control (RBAC) for Foresight AI.
Defines roles, permissions, and route/endpoint access policies.
"""

from typing import Dict, Set, Optional

ROLE_ADMIN = "ADMIN"
ROLE_ANALYST = "ANALYST"
ROLE_VIEWER = "VIEWER"

VALID_ROLES = {ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER}

# Permission sets per role
PERMISSIONS: Dict[str, Set[str]] = {
    ROLE_ADMIN: {
        "view:dashboard",
        "view:forecast",
        "view:inventory",
        "view:stockout",
        "view:reorder",
        "action:reorder",
        "view:products",
        "view:quality",
        "view:models",
        "export:csv",
        "admin:users",
        "admin:security",
        "admin:audit",
    },
    ROLE_ANALYST: {
        "view:dashboard",
        "view:forecast",
        "view:inventory",
        "view:stockout",
        "view:reorder",
        "action:reorder",
        "view:products",
        "view:quality",
        "view:models",
        "export:csv",
    },
    ROLE_VIEWER: {
        "view:dashboard",
        "view:products",
        "export:csv",
    },
}

# Protected API Endpoints requiring specific permissions
ENDPOINT_PERMISSIONS = {
    "/api/admin/users": "admin:users",
    "/api/admin/users/status": "admin:users",
    "/api/admin/users/role": "admin:users",
    "/api/admin/users/reset-password": "admin:users",
    "/api/admin/security-status": "admin:security",
    "/api/inventory": "view:inventory",
    "/api/forecast": "view:forecast",
    "/api/stockout": "view:stockout",
    "/api/reorder": "view:reorder",
    "/api/quality": "view:quality",
    "/api/models": "view:models",
    "/api/overview": "view:dashboard",
    "/api/summary": "view:dashboard",
    "/api/products": "view:products",
    "/api/analytics": "view:products",
    "/api/sales": "view:dashboard",
    "/api/insights": "view:dashboard",
    "/api/export/inventory": "view:inventory",
    "/api/export/stockout": "view:stockout",
    "/api/export/reorder": "view:reorder",
    "/api/export/products": "view:products",
}


class RBAC:
    """Evaluates role permissions and route access."""

    @staticmethod
    def has_permission(role: str, permission: str) -> bool:
        user_perms = PERMISSIONS.get(role.upper(), set())
        return permission in user_perms

    @staticmethod
    def can_access_endpoint(role: str, path: str) -> bool:
        clean_path = path.split("?")[0]
        # Exact match or prefix match for export
        required_perm = ENDPOINT_PERMISSIONS.get(clean_path)
        if not required_perm:
            # Check prefix matches
            for prefix, perm in ENDPOINT_PERMISSIONS.items():
                if clean_path.startswith(prefix):
                    required_perm = perm
                    break

        if not required_perm:
            # General authenticated endpoints (e.g. /api/auth/me, /api/auth/change-password)
            return True

        return RBAC.has_permission(role, required_perm)
