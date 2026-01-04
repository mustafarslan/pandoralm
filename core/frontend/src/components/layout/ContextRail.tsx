import React, { useEffect } from 'react';
import { useLayerStore } from '../../store/useLayerStore';
import { Check, Shield } from 'lucide-react';

const LayerItem = ({ layer, isActive, onToggle }) => {
    return (
        <div
            onClick={() => onToggle(layer.id)}
            className={`
        flex items-center gap-3 p-3 rounded-lg cursor-pointer border transition-all
        ${isActive
                    ? 'bg-blue-500/10 border-blue-500/50 text-blue-100'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800 hover:border-slate-700'}
      `}
        >
            <div className={`w-2 h-full rounded-full bg-${layer.color || 'slate'}-500`} />
            <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{layer.name}</div>
                <div className="text-xs opacity-60 flex items-center gap-1">
                    <Shield size={10} />
                    {layer.type}
                </div>
            </div>
            {isActive && <Check size={16} className="text-blue-400" />}
        </div>
    );
};

const ContextRail = () => {
    const { availableLayers, activeLayerIds, toggleLayer, setLayers } = useLayerStore();

    // Simulate fetching layers on mount (Phase 1.1)
    useEffect(() => {
        // In real implementation this fetches from /api/v1/auth/layers
        // For now we mock it to allow UI development
        if (availableLayers.length === 0) {
            setLayers([
                { id: 'layer_system', name: 'System Public', type: 'SYSTEM', color: 'slate' },
                { id: 'layer_eng', name: 'Engineering', type: 'ORG', color: 'blue' },
                { id: 'layer_hr', name: 'Human Resources', type: 'ORG', color: 'rose' },
                { id: 'layer_private', name: 'My Workspace', type: 'USER', color: 'emerald' },
            ]);
        }
    }, [availableLayers.length, setLayers]);

    return (
        <div className="h-full w-full bg-slate-925 flex flex-col p-4 border-r border-slate-800">
            <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">
                Active Context
            </h2>

            <div className="flex-1 overflow-y-auto space-y-2">
                {availableLayers.map(layer => (
                    <LayerItem
                        key={layer.id}
                        layer={layer}
                        isActive={activeLayerIds.includes(layer.id)}
                        onToggle={toggleLayer}
                    />
                ))}
            </div>

            <div className="p-4 bg-slate-900 rounded-lg mt-4 border border-slate-800">
                <div className="text-xs text-slate-400 mb-2">Memory Usage</div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-purple-500 h-full w-[45%]" />
                </div>
            </div>
        </div>
    );
};

export default ContextRail;
