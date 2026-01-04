import React, { useState, useEffect } from 'react';
import { Search, Network, Merge, Trash2, Loader2, RefreshCw, Layers } from 'lucide-react';
import { cortexGet, cortexPost } from '@/utils/cortexApi';
import showToast from '@/utils/toast';

export default function EntityManager() {
    const [entities, setEntities] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedEntities, setSelectedEntities] = useState<string[]>([]);
    const [merging, setMerging] = useState(false);

    // Layer state (Replacing Workspace state)
    const [layerId, setLayerId] = useState('system_core');
    const [layers, setLayers] = useState<any[]>([]);

    useEffect(() => {
        const fetchLayers = async () => {
            try {
                const data = await cortexGet<any[]>('/api/v1/ops/layers');
                if (data && Array.isArray(data)) {
                    setLayers(data);
                }
            } catch (e) {
                console.error("Failed to fetch layers", e);
            }
        };
        fetchLayers();
    }, []);

    const fetchEntities = async () => {
        setLoading(true);
        try {
            // Pass layerId as workspace_id param to leveraging the scatter-gather backend logic
            const res = await cortexGet<any>(`/api/v1/ops/graph/entities?workspace_id=${layerId}`);
            if (res && res.entities && Array.isArray(res.entities)) {
                setEntities(res.entities);
            } else {
                setEntities([]);
            }
        } catch (e) {
            console.error(e);
            setEntities([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchEntities();
    }, [layerId]);

    const handleMerge = async () => {
        if (selectedEntities.length < 2) return;
        setMerging(true);
        try {
            await cortexPost('/api/v1/ops/graph/merge', {
                target_id: selectedEntities[0],
                source_ids: selectedEntities.slice(1),
                workspace_id: layerId
            });
            showToast('Entities merged successfully', 'success');
            setSelectedEntities([]);
            fetchEntities();
        } catch (e) {
            showToast('Failed to merge entities', 'error');
        } finally {
            setMerging(false);
        }
    };

    const toggleSelection = (id: string) => {
        setSelectedEntities(prev =>
            prev.includes(id) ? prev.filter(e => e !== id) : [...prev, id]
        );
    };

    return (
        <div className="p-4 space-y-4">
            <div className="flex justify-between items-center">
                <div>
                    <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Entity Manager</h3>
                    <p className="text-sm text-[var(--ink-meta)]">
                        Explore and consolidate entities extracted by GraphRAG.
                    </p>
                </div>
                <div className="flex gap-2 items-center">
                    <select
                        value={layerId}
                        onChange={(e) => setLayerId(e.target.value)}
                        className="px-3 py-1.5 text-sm rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-violet-500/20"
                    >
                        {layers.map((layer) => (
                            <option key={layer.id} value={layer.id}>
                                {layer.name} ({layer.type})
                            </option>
                        ))}
                    </select>

                    {selectedEntities.length >= 2 && (
                        <button
                            onClick={handleMerge}
                            disabled={merging}
                            className="flex items-center gap-2 px-3 py-1.5 bg-[var(--ink-heading)] text-white rounded-lg text-xs font-medium hover:bg-black/80 transition-colors"
                        >
                            {merging ? <Loader2 size={14} className="animate-spin" /> : <Merge size={14} />}
                            Merge Selected ({selectedEntities.length})
                        </button>
                    )}
                    <button
                        onClick={fetchEntities}
                        disabled={loading}
                        className="p-2 text-[var(--ink-meta)] hover:text-[var(--ink-heading)] hover:bg-[var(--ink-border)]/50 rounded-lg transition-colors"
                    >
                        <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                    </button>
                </div>
            </div>

            <div className="overflow-x-auto border border-[var(--ink-border)] rounded-lg">
                <table className="w-full text-sm text-left">
                    <thead className="bg-[var(--ink-card)] text-[var(--ink-meta)] uppercase text-[10px] font-bold tracking-wider">
                        <tr>
                            <th className="px-4 py-3 w-10">
                                <input type="checkbox" disabled />
                            </th>
                            <th className="px-4 py-3">Entity Name</th>
                            <th className="px-4 py-3">Type</th>
                            <th className="px-4 py-3">Mentions</th>
                            <th className="px-4 py-3">Sources</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--ink-border)] bg-white">
                        {loading ? (
                            <tr>
                                <td colSpan={5} className="py-12 text-center">
                                    <Loader2 size={24} className="animate-spin text-[var(--ink-meta)] mx-auto" />
                                </td>
                            </tr>
                        ) : entities.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="py-8 text-center text-[var(--ink-meta)]">
                                    No entities found in this layer.
                                </td>
                            </tr>
                        ) : entities.map((entity) => (
                            <tr
                                key={entity.id}
                                className={`hover:bg-[var(--ink-page)] transition-colors cursor-pointer ${selectedEntities.includes(entity.id) ? 'bg-[var(--ink-page)] border-l-2 border-black' : ''}`}
                                onClick={() => toggleSelection(entity.id)}
                            >
                                <td className="px-4 py-3">
                                    <input
                                        type="checkbox"
                                        checked={selectedEntities.includes(entity.id)}
                                        onChange={() => { }}
                                        className="cursor-pointer"
                                    />
                                </td>
                                <td className="px-4 py-3 font-medium text-[var(--ink-heading)]">
                                    {entity.name}
                                </td>
                                <td className="px-4 py-3">
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border border-[var(--ink-border)] bg-[var(--ink-bg)] text-[var(--ink-heading)]`}>
                                        {entity.type}
                                    </span>
                                </td>
                                <td className="px-4 py-3 text-[var(--ink-meta)]">
                                    {entity.mention_count}
                                </td>
                                <td className="px-4 py-3 text-[var(--ink-meta)] text-xs">
                                    {entity.source_documents?.length || 0} docs
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
