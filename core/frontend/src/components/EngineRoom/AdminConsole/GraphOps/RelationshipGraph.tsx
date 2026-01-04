import React, { useState, useEffect, useRef } from 'react';
import { Network, Search, Loader2, X, RefreshCw, Layers } from 'lucide-react';
import { cortexGet, cortexDelete } from '@/utils/cortexApi';
import showToast from '@/utils/toast';

export default function RelationshipGraph() {
    const [loading, setLoading] = useState(false);
    const [docId, setDocId] = useState('');

    // Layer state
    const [layerId, setLayerId] = useState('system_core');
    const [layers, setLayers] = useState<any[]>([]);

    // Placeholder for graph - in real implementation use react-force-graph-2d
    const containerRef = useRef<HTMLDivElement>(null);

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

    // Example of how we would fetch relationships if visualization was implemented
    const fetchRelationships = async () => {
        if (!docId) return;
        setLoading(true);
        try {
            // Pass layerId as workspace_id param
            const res = await cortexGet(`/api/v1/ops/graph/relationships/${docId}?workspace_id=${layerId}`);
            // setGraphData(res);
        } catch (e) {
            console.error(e);
            showToast("Failed to fetch graph data", 'error');
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="p-4 space-y-4 h-full flex flex-col">
            <div className="flex justify-between items-center">
                <div>
                    <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Relationship Inspector</h3>
                    <p className="text-sm text-[var(--ink-meta)]">
                        Visualize and audit extracted relationships for a specific document.
                    </p>
                </div>
                <div className="flex items-center gap-2">
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
                </div>
            </div>

            <div className="flex gap-2">
                <div className="relative flex-1 max-w-md">
                    <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ink-meta)]" />
                    <input
                        type="text"
                        value={docId}
                        onChange={(e) => setDocId(e.target.value)}
                        placeholder="Enter Document ID to visualize..."
                        className="w-full pl-9 pr-3 py-1.5 text-sm rounded-lg border border-[var(--ink-border)] bg-white focus:outline-none focus:ring-2 focus:ring-black/5"
                    />
                </div>
                <button
                    className="px-4 py-1.5 bg-[var(--ink-heading)] text-white rounded-lg text-sm font-medium hover:bg-black/80 transition-colors"
                    onClick={fetchRelationships}
                >
                    Visualise
                </button>
            </div>

            <div
                ref={containerRef}
                className="flex-1 bg-[var(--ink-bg)] rounded-xl border border-[var(--ink-border)] relative overflow-hidden min-h-[400px] flex items-center justify-center"
            >
                {loading ? (
                    <div className="text-center">
                        <Loader2 size={32} className="animate-spin text-[var(--ink-heading)] mx-auto mb-2" />
                        <p className="text-xs text-[var(--ink-meta)]">Constructing Knowledge Graph...</p>
                    </div>
                ) : docId ? (
                    <div className="text-center p-8">
                        <Network size={48} className="text-slate-200 mx-auto mb-4" />
                        <p className="text-sm text-[var(--ink-meta)]">
                            Graph visualization mock. <br />
                            Layer: {layerId}
                        </p>
                    </div>
                ) : (
                    <div className="text-center text-[var(--ink-meta)]">
                        <p>Enter a document ID to start inspection</p>
                    </div>
                )}
            </div>

            {docId && !loading && (
                <div className="bg-white border border-[var(--ink-border)] rounded-lg p-3 text-xs">
                    <h4 className="font-bold text-[var(--ink-heading)] mb-2">Selected Relationship</h4>
                    <div className="flex items-center gap-2 mb-2">
                        <span className="px-2 py-0.5 border border-[var(--ink-border)] rounded font-medium">Mustafa Arslan</span>
                        <span className="text-[var(--ink-meta)] text-[10px] uppercase">WORKS_ON</span>
                        <span className="px-2 py-0.5 border border-[var(--ink-border)] rounded font-medium">Project Pandora</span>
                    </div>
                    <button className="text-[var(--ink-heading)] hover:bg-[var(--ink-page)] px-2 py-1 rounded flex items-center gap-1 font-medium transition-colors border border-[var(--ink-border)]">
                        <X size={12} /> Delete Relationship
                    </button>
                </div>
            )}
        </div>
    );
}
