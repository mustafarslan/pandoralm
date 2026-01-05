import React, { useState, useEffect, useRef } from 'react';
import { Network, Search, Loader2, X, RefreshCw, Layers } from 'lucide-react';
import { cortexGet, cortexDelete } from '@/utils/cortexApi';
import showToast from '@/utils/toast';
import { GraphViewer } from '@/components/GraphViewer';

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
                        <option value="global">Global Knowledge Graph</option>
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
                className="flex-1 bg-[var(--ink-bg)] rounded-xl border border-[var(--ink-border)] relative overflow-hidden min-h-[400px] flex items-center justify-center p-0"
            >
                <GraphViewer
                    workspaceId={layerId}
                    height="100%"
                    apiBaseUrl="/api/v1"
                />
            </div>

            {/* 
            {docId && !loading && (
                <div className="bg-white border border-[var(--ink-border)] rounded-lg p-3 text-xs">
                    // Implementation needed for relationship details
                </div>
            )} 
            */}
        </div>
    );
}
