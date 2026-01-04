/**
 * Cortex API Client
 * 
 * Centralized fetch wrapper for Pandora Cortex API calls.
 * Automatically injects X-Pandora-Layer-ID header from the LayerStore.
 */
import { useLayerStore } from '@/store/useLayerStore';

// Debug: Force absolute URL to bypass Vite Proxy/Env issues
const CORTEX_API = "http://localhost:8000";
// const CORTEX_API = import.meta.env.VITE_CORTEX_API_URL || "http://localhost:8000";

/**
 * Get base headers for Cortex API calls
 * Includes auth token and layer context
 */
export function getCortexHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
    };

    // Add auth token
    const authToken = localStorage.getItem('pandoralm_authToken');
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    // Add layer context from store (ReBAC enforcement)
    const layerHeaders = useLayerStore.getState().getActiveLayerHeaders();
    Object.assign(headers, layerHeaders);

    return headers;
}

/**
 * Fetch wrapper for Cortex API
 * Automatically adds auth and layer headers
 */
export async function cortexFetch(
    endpoint: string,
    options: RequestInit = {}
): Promise<Response> {
    const url = endpoint.startsWith('http')
        ? endpoint
        : `${CORTEX_API}${endpoint}`;

    const headers = getCortexHeaders();

    // Merge with any provided headers
    if (options.headers) {
        const providedHeaders = options.headers as Record<string, string>;
        Object.assign(headers, providedHeaders);
    }

    return fetch(url, {
        ...options,
        headers,
    });
}

/**
 * Typed GET request
 */
export async function cortexGet<T>(endpoint: string): Promise<T> {
    const response = await cortexFetch(endpoint);
    if (!response.ok) {
        throw new Error(`Cortex API error: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Typed POST request
 */
export async function cortexPost<T>(
    endpoint: string,
    data?: unknown
): Promise<T> {
    const response = await cortexFetch(endpoint, {
        method: 'POST',
        body: data ? JSON.stringify(data) : undefined,
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Cortex API error: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Typed PATCH request
 */
export async function cortexPatch<T>(
    endpoint: string,
    data?: unknown
): Promise<T> {
    const response = await cortexFetch(endpoint, {
        method: 'PATCH',
        body: data ? JSON.stringify(data) : undefined,
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Cortex API error: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Typed DELETE request
 */
export async function cortexDelete<T>(
    endpoint: string,
    data?: unknown
): Promise<T> {
    const response = await cortexFetch(endpoint, {
        method: 'DELETE',
        body: data ? JSON.stringify(data) : undefined,
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Cortex API error: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Hook to get current layer headers for manual fetch calls
 * Use this when you need to pass headers to third-party libraries
 */
export function useLayerHeaders(): Record<string, string> {
    return useLayerStore.getState().getActiveLayerHeaders();
}

export { CORTEX_API };
export default cortexFetch;
