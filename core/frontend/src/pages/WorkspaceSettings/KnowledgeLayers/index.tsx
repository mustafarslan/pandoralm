import React, { useEffect } from 'react';
import { useLayerStore } from '@/store/useLayerStore';
import { Layers, HardDrive, Shield, Lock, Info } from 'lucide-react';

export default function KnowledgeLayersSettings() {
    const { availableLayers, fetchLayers, isLoading } = useLayerStore();

    useEffect(() => {
        fetchLayers();
    }, [fetchLayers]);

    // Separate layers
    const myLayer = availableLayers.find(l => l.type === 'USER');
    const sharedLayers = availableLayers.filter(l => l.type !== 'USER');

    const formatBytes = (bytes?: number) => {
        if (bytes === undefined) return '0 B';
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const getUsagePercent = (used: number = 0, total: number = 104857600) => {
        if (!total || total === 0) return 0;
        return Math.min(100, Math.max(0, (used / total) * 100));
    };

    if (isLoading) {
        return (
            <div className="flex h-full w-full items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--ink-primary)]"></div>
            </div>
        );
    }

    return (
        <div className="w-full h-full flex flex-col gap-y-6 overflow-y-scroll pr-4">
            {/* Header */}
            <div>
                <h2 className="text-xl font-bold text-[var(--ink-heading)] flex items-center gap-2">
                    <Layers className="text-[var(--ink-primary)]" /> Knowledge Layers
                </h2>
                <p className="text-sm text-[var(--ink-muted)] mt-1">
                    Manage your private knowledge layer and view shared organizational layers you have access to.
                </p>
            </div>

            {/* My Private Layer Card */}
            {myLayer && (
                <div className="bg-white rounded-lg border border-[var(--ink-border)] shadow-sm p-6">
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <h3 className="text-base font-bold text-[var(--ink-heading)] flex items-center gap-2">
                                <Lock size={16} className="text-amber-500" /> My Private Layer
                            </h3>
                            <p className="text-xs text-[var(--ink-muted)]">
                                Only you can see data in this layer.
                            </p>
                        </div>
                        <span className="text-xs font-mono bg-slate-100 text-slate-600 px-2 py-1 rounded border border-slate-200">
                            {myLayer.quota_tier || 'FREE'} TIER
                        </span>
                    </div>

                    <div className="space-y-2">
                        <div className="flex justify-between text-xs font-medium text-[var(--ink-primary)]">
                            <span>Storage Usage</span>
                            <span>
                                {formatBytes(myLayer.storage_used_bytes)} / {formatBytes(myLayer.storage_quota_bytes)}
                            </span>
                        </div>
                        <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden relative">
                            <div
                                className={`h-full rounded-full transition-all duration-500 absolute left-0 top-0 ${getUsagePercent(myLayer.storage_used_bytes, myLayer.storage_quota_bytes) > 90
                                        ? 'bg-red-500'
                                        : 'bg-[#252525]' // ink-primary
                                    }`}
                                style={{ width: `${getUsagePercent(myLayer.storage_used_bytes, myLayer.storage_quota_bytes)}%` }}
                            />
                        </div>
                        {getUsagePercent(myLayer.storage_used_bytes, myLayer.storage_quota_bytes) > 90 && (
                            <p className="text-xs text-red-500 flex items-center gap-1 mt-1 font-bold">
                                <Info size={12} /> Warning: You are approaching your storage limit.
                            </p>
                        )}
                        <p className="text-[10px] text-[var(--ink-muted)] text-right mt-1">
                            {getUsagePercent(myLayer.storage_used_bytes, myLayer.storage_quota_bytes).toFixed(1)}% Used
                        </p>
                    </div>
                </div>
            )}

            {/* Shared Layers List */}
            <div className="bg-white rounded-lg border border-[var(--ink-border)] shadow-sm p-6">
                <h3 className="text-base font-bold text-[var(--ink-heading)] mb-4 flex items-center gap-2">
                    <Shield size={16} className="text-blue-500" /> Shared Layers
                </h3>

                <div className="space-y-3">
                    {sharedLayers.length === 0 ? (
                        <p className="text-sm text-[var(--ink-muted)] italic">No shared layers found.</p>
                    ) : (
                        sharedLayers.map(layer => (
                            <div key={layer.id} className="flex items-center justify-between p-3 border border-slate-100 rounded hover:bg-slate-50 transition-colors">
                                <div className="flex items-center gap-3">
                                    <div className={`p-2 rounded-full ${layer.type === 'SYSTEM' ? 'bg-blue-100 text-blue-600' :
                                            layer.type === 'ORG' ? 'bg-purple-100 text-purple-600' :
                                                'bg-emerald-100 text-emerald-600'
                                        }`}>
                                        <Layers size={16} />
                                    </div>
                                    <div>
                                        <div className="font-medium text-sm text-[var(--ink-heading)]">{layer.name}</div>
                                        <div className="text-xs text-[var(--ink-muted)] font-mono">{layer.type}</div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2">
                                    {/* Access Badges */}
                                    {layer.access === 'ADMIN' && (
                                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-700 border border-amber-200">ADMIN</span>
                                    )}
                                    {(layer.access === 'WRITE' || layer.access === 'ADMIN') && (
                                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-green-100 text-green-700 border border-green-200">WRITE</span>
                                    )}
                                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-700 border border-blue-200">READ</span>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
