import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import System from '../models/system';

// Knowledge Layer Types based on ReBAC architecture
type AccessLevel = 'READ' | 'WRITE' | 'ADMIN';

interface Layer {
    id: string;
    name: string;
    type: 'SYSTEM' | 'ORG' | 'TEAM' | 'USER';
    color: string;
    access: AccessLevel;
    permissions: string[];
    quota_tier?: 'FREE' | 'PRO' | 'ENTERPRISE';
    storage_quota_bytes?: number;
    storage_used_bytes?: number;
    owner_user_id?: string;
}

interface LayerState {
    activeLayerIds: string[];
    availableLayers: Layer[];
    isLoading: boolean;
    toggleLayer: (layerId: string) => void;
    setLayers: (layers: Layer[]) => void;
    setActiveLayers: (ids: string[]) => void;
    getActiveLayerHeaders: () => Record<string, string>;
    hasWriteAccess: (layerId: string) => boolean;
    canAccessLayer: (layerId: string) => boolean;
    fetchLayers: (workspaceId: string) => Promise<void>;
}

export const useLayerStore = create<LayerState>()(
    persist(
        (set, get) => ({
            activeLayerIds: [],
            availableLayers: [],
            isLoading: true,

            toggleLayer: (layerId: string) =>
                set((state) => {
                    const isActive = state.activeLayerIds.includes(layerId);
                    return {
                        activeLayerIds: isActive
                            ? state.activeLayerIds.filter((id) => id !== layerId)
                            : [...state.activeLayerIds, layerId],
                    };
                }),

            setLayers: (layers: Layer[]) => set({ availableLayers: layers, isLoading: false }),

            setActiveLayers: (ids: string[]) => set({ activeLayerIds: ids }),

            /**
             * Returns headers to inject into API calls for layer-scoped requests.
             * This is critical for ReBAC enforcement on the backend.
             */
            getActiveLayerHeaders: (): Record<string, string> => {
                const { activeLayerIds } = get();
                if (activeLayerIds.length === 0) return {};
                return {
                    'X-Pandora-Layer-ID': activeLayerIds.join(','),
                };
            },

            /**
             * Check if the user has WRITE or ADMIN access to a specific layer.
             */
            hasWriteAccess: (layerId: string): boolean => {
                const { availableLayers } = get();
                const layer = availableLayers.find((l) => l.id === layerId);
                return layer ? ['WRITE', 'ADMIN'].includes(layer.access) : false;
            },

            /**
             * Check if the user can access a layer at all (READ, WRITE, or ADMIN).
             */
            canAccessLayer: (layerId: string): boolean => {
                const { availableLayers } = get();
                return availableLayers.some((l) => l.id === layerId);
            },

            fetchLayers: async (workspaceId: string) => {
                set({ isLoading: true });
                const layers = await System.getWorkspaceLayers(workspaceId);
                if (Array.isArray(layers)) {
                    const mapped = layers.map((l: any) => ({
                        id: l.id,
                        name: l.name,
                        type: l.type,
                        color: l.color,
                        access: (l.access_mode === 'write' ? 'WRITE' : 'READ') as AccessLevel, // Mapping access_mode
                        permissions: [],
                        quota_tier: l.quota_tier,
                        storage_quota_bytes: l.storage_quota_bytes,
                        storage_used_bytes: l.storage_used_bytes,
                        owner_user_id: l.owner_user_id
                    }));
                    set({ availableLayers: mapped, isLoading: false });
                } else {
                    set({ isLoading: false });
                }
            },
        }),
        {
            name: 'pandora-layer-storage', // name of the item in the storage (must be unique)
        }
    )
);

/**
 * Helper hook to get the X-Pandora-Layer-ID header value for API calls.
 * Use this in fetch wrappers or axios interceptors.
 */
export const getLayerHeaders = (): Record<string, string> => {
    return useLayerStore.getState().getActiveLayerHeaders();
};
