import { AUTH_TOKEN } from './constants';

export function getAuthToken(): string | null {
    return window.localStorage.getItem(AUTH_TOKEN);
}

function decodeJwt(token: string): any {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
            window
                .atob(base64)
                .split('')
                .map(function (c) {
                    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                })
                .join('')
        );
        return JSON.parse(jsonPayload);
    } catch (e) {
        return null;
    }
}

export function getUserRoles(): string[] {
    const token = getAuthToken();
    if (!token) {
        // Development/staging fallback - check both DEV mode and explicit skip flag
        const isDevMode = import.meta.env.DEV;
        const skipAuth = import.meta.env.VITE_DEV_MODE_SKIP_AUTH === 'true';
        if (isDevMode || skipAuth) {
            return ['admin', 'vector-ops'];
        }
        return [];
    }

    const payload = decodeJwt(token);
    if (!payload) return [];

    // Core JWT: role is a direct field (e.g., "admin", "manager", "default")
    // This is the primary auth mechanism for PandoraLM
    if (payload.role) {
        return [payload.role];
    }

    // Keycloak JWT: roles are in resource_access or realm_access
    // Kept for backwards compatibility with Keycloak-based deployments
    const roles = payload?.resource_access?.pandora?.roles || [];
    const realmRoles = payload?.realm_access?.roles || [];

    return [...new Set([...roles, ...realmRoles])];
}

export function hasRole(role: string): boolean {
    return getUserRoles().includes(role);
}

export function isAdmin(): boolean {
    return hasRole('admin');
}

export function canWriteVectors(): boolean {
    return hasRole('vector-ops') || isAdmin();
}
