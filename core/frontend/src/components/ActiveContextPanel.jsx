import React, { useCallback, useEffect, useState } from 'react';
import { Globe, Building2, Users, Lock } from 'lucide-react';
import { useLayerStore } from '@/store/useLayerStore';
import System from '@/models/system';

// Simple cn utility
function cn(...classes) {
    return classes.filter(Boolean).join(' ');
}

// Layer Badge Component
const LayerBadge = ({ layer, isActive, isCompact, onClick }) => {
    // Map types to Lucide Icons
    const TypeIcon = {
        SYSTEM: Lock,
        ORG: Building2,
        TEAM: Users,
        USER: Globe,
    }[layer.type] || Globe;

    // Ink Wash Semantic Mapping (Dark on Light)
    // Ink Wash Semantic Mapping (Monochrome/Ink)
    const typeStyles = {
        SYSTEM: 'bg-ink-panel border-ink-border/40 text-ink-primary',
        ORG: 'bg-ink-panel border-ink-border/40 text-ink-primary',
        TEAM: 'bg-ink-panel border-ink-border/40 text-ink-primary',
        USER: 'bg-ink-panel border-ink-border/40 text-ink-primary',
    };

    const isImmutable = layer.type === 'SYSTEM';

    // Active state uses Ink Action (Charcoal)
    if (isActive) {
        if (isCompact) {
            return (
                <button
                    onClick={isImmutable ? undefined : onClick}
                    className="w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-200 bg-ink-action text-white shadow-md"
                    title={`${layer.name} (${layer.type})`}
                    disabled={isImmutable}
                >
                    <TypeIcon size={18} />
                </button>
            );
        }
        return (
            <button
                onClick={isImmutable ? undefined : onClick}
                disabled={isImmutable}
                className="w-full p-3 rounded-lg flex items-center gap-3 transition-all duration-200 bg-ink-panel border border-ink-border/20 shadow-sm"
            >
                <div className="w-8 h-8 rounded-md flex items-center justify-center text-xs font-bold bg-ink-action text-white">
                    {layer.access === 'ADMIN' ? 'A' : layer.access === 'WRITE' ? 'W' : 'R'}
                </div>
                <div className="flex-1 text-left min-w-0">
                    <p className="text-sm font-medium text-ink-primary truncate">{layer.name}</p>
                    <p className="text-[10px] text-ink-muted uppercase tracking-wider">{layer.type}</p>
                </div>
                <div className="w-1.5 h-6 rounded-full bg-ink-action" />
            </button>
        );
    }

    // Inactive State
    const inactiveIconStyle = typeStyles[layer.type] || 'text-ink-muted border-ink-border/10 bg-ink-page';

    if (isCompact) {
        return (
            <button
                onClick={isImmutable ? undefined : onClick}
                className={cn(
                    "w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-200 border",
                    "bg-ink-page hover:bg-ink-panel",
                    inactiveIconStyle
                )}
                title={`${layer.name} (${layer.type})`}
                disabled={isImmutable}
            >
                <TypeIcon size={18} />
            </button>
        );
    }

    return (
        <button
            onClick={isImmutable ? undefined : onClick}
            disabled={isImmutable}
            className={cn(
                "w-full p-3 rounded-lg flex items-center gap-3 transition-all duration-200 border border-transparent hover:bg-ink-panel",
                isImmutable ? "cursor-default opacity-80" : "cursor-pointer"
            )}
        >
            <div className={cn(
                "w-8 h-8 rounded-md flex items-center justify-center text-xs font-bold border",
                inactiveIconStyle
            )}>
                {layer.access === 'ADMIN' ? 'A' : layer.access === 'WRITE' ? 'W' : 'R'}
            </div>
            <div className="flex-1 text-left min-w-0">
                <p className="text-sm font-medium text-ink-muted group-hover:text-ink-primary truncate">{layer.name}</p>
                <p className="text-[10px] text-ink-muted/70 uppercase tracking-wider">{layer.type}</p>
            </div>
        </button>
    );
};

const ActiveContextPanel = ({ isCompact }) => {
    const { availableLayers, activeLayerIds, setLayers, setActiveLayers } = useLayerStore();
    const [isLoadingLayers, setIsLoadingLayers] = useState(false);

    // Hardcoded State for UI/UX Refactor
    useEffect(() => {
        const mockLayers = [
            { id: 'sys', name: 'System', type: 'SYSTEM', color: 'slate', access: 'READ', permissions: ['read'] },
            { id: 'org', name: 'Organization', type: 'ORG', color: 'violet', access: 'READ', permissions: ['read'] },
            { id: 'team', name: 'Engineering', type: 'TEAM', color: 'blue', access: 'WRITE', permissions: ['read', 'write'] },
            { id: 'me', name: 'Private', type: 'USER', color: 'emerald', access: 'ADMIN', permissions: ['read', 'write', 'admin'] },
        ];

        setLayers(mockLayers);
        // Default to System and Organization as active if nothing selected
        if (activeLayerIds.length === 0) {
            setActiveLayers(['sys', 'org']);
        }
    }, [setLayers, setActiveLayers, activeLayerIds.length]);



    const handleLayerSelect = (layerId) => {
        const layer = availableLayers.find(l => l.id === layerId);
        if (layer?.type === 'SYSTEM') return; // Immutable
        // Toggle logic if we want multi-select, or just set if single select (minus system)
        // For ReBAC, usually we add/remove to the set. Use toggleLayer from store if available or implement here.
        // Assuming single select + system or multi-select.
        // Current useLayerStore has toggleLayer. Let's use it for better UX or stick to setActiveLayers but keeping System.
        // If we want System ALWAYS on, we should ensure it's in the list.

        // Let's implement toggle logic but ensure SYSTEM is kept.
        const isSystem = layerId === 'layer_system' || layer?.type === 'SYSTEM';
        if (isSystem) return;

        const newActive = activeLayerIds.includes(layerId)
            ? activeLayerIds.filter(id => id !== layerId)
            : [...activeLayerIds, layerId];

        // Ensure system layer is always present if it exists
        const systemLayer = availableLayers.find(l => l.type === 'SYSTEM');
        if (systemLayer && !newActive.includes(systemLayer.id)) {
            newActive.push(systemLayer.id);
        }

        setActiveLayers(newActive);
    };

    return (
        <div className={cn(
            "space-y-2",
            isCompact && "flex flex-col items-center"
        )}>
            {!isCompact && (
                <p className="text-[10px] font-bold text-ink-muted uppercase tracking-widest px-2 mb-2">
                    Active Context
                </p>
            )}
            {isLoadingLayers ? (
                <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-ink-action" />
                </div>
            ) : (
                availableLayers.map((layer) => (
                    <LayerBadge
                        key={layer.id}
                        layer={layer}
                        isActive={activeLayerIds.includes(layer.id)}
                        isCompact={isCompact}
                        onClick={() => handleLayerSelect(layer.id)}
                    />
                ))
            )}
        </div>
    );
};

export default ActiveContextPanel;
