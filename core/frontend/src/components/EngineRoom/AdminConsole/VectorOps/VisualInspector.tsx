import React, { useState, useEffect } from 'react';
import { Search, Hash, FileText, Database, Loader2, RefreshCw } from 'lucide-react';
import { cortexGet } from '@/utils/cortexApi';
import showToast from '@/utils/toast';

export default function VisualInspector() {
    const [loading, setLoading] = useState(false);
    // FIXED: Use window location or storage to find active workspace, fallback to first available
    const [workspaceId, setWorkspaceId] = useState(() => {
        // Attempt to get from URL first /workspace/:slug/...
        const matches = window.location.pathname.match(/\/workspace\/([^\/]+)/);
        if (matches && matches[1]) return matches[1];
        return 'default';
    });
    const [chunks, setChunks] = useState<any[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize] = useState(20);

    const [layers, setLayers] = useState<any[]>([]);

    // Fetch Layers (Contexts) instead of legacy Workspaces
    useEffect(() => {
        const fetchLayers = async () => {
            try {
                const res = await cortexGet<any>('/api/v1/ops/layers?include_vector_counts=true');
                if (res) {
                    // Api returns { layers: [...] } or just array? checking ops.py list_layers returns List[Dict] directly?
                    // Wait, ops.py:782 says "-> List[Dict[str, Any]]" but let's check return
                    // It likely returns JSON array.
                    // Actually, let's look at the return of list_layers in previous turn.
                    // It matches the return type hint.
                    // However, standard cortexGet might wrap it? 
                    // Let's assume it returns array directly or we adapt.
                    const layerList = Array.isArray(res) ? res : (res.layers || []);
                    setLayers(layerList);

                    // Default to first layer if current workspaceId not found
                    const validIds = layerList.map((l: any) => l.id);
                    if (!validIds.includes(workspaceId) && validIds.length > 0) {
                        setWorkspaceId(validIds[0]);
                    }
                }
            } catch (e) {
                console.error("Failed to fetch layers", e);
            }
        };
        fetchLayers();
    }, []);

    const fetchChunks = async () => {
        setLoading(true);
        try {
            // Correct endpoint path matching ops.py registration
            const res = await cortexGet<any>(`/api/v1/ops/vectors/inspect/${workspaceId}?page=${page}&page_size=${pageSize}`);
            setChunks(res.chunks || []);
            setTotal(res.total || 0);
        } catch (e) {
            console.error(e);
            showToast("Failed to fetch vector chunks", "error");
            setChunks([]);
            setTotal(0);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchChunks();
    }, [page, workspaceId]);

    return (
        <div className="p-4 space-y-4">
            <div className="flex justify-between items-center">
                <div>
                    <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Visual Inspector</h3>
                    <p className="text-sm text-[var(--ink-meta)]">
                        Explore and inspect raw text vectors stored in LanceDB.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <select
                        value={workspaceId}
                        onChange={(e) => setWorkspaceId(e.target.value)}
                        className="px-3 py-1.5 text-sm rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-violet-500/20"
                    >
                        {layers.length === 0 && <option value="default">Default Layer</option>}
                        {layers.map((layer) => (
                            <option key={layer.id} value={layer.id}>
                                {layer.name} ({layer.type})
                            </option>
                        ))}
                    </select>
                    <button
                        onClick={fetchChunks}
                        disabled={loading}
                        className="p-2 text-[var(--ink-meta)] hover:text-[var(--ink-heading)] hover:bg-[var(--ink-border)]/50 rounded-lg transition-colors"
                        title="Refresh"
                    >
                        <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                    </button>
                </div>
            </div>

            {/* Filters (Placeholder) */}
            <div className="flex gap-2">
                <div className="relative flex-1">
                    <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ink-meta)]" />
                    <input
                        type="text"
                        placeholder="Search by content or document ID..."
                        className="w-full pl-9 pr-3 py-1.5 text-sm rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] placeholder:text-[var(--ink-meta)] focus:outline-none focus:ring-2 focus:ring-violet-500/20"
                    />
                </div>
            </div>

            {/* Data Table */}
            <div className="overflow-x-auto border border-[var(--ink-border)] rounded-lg">
                <table className="w-full text-sm text-left">
                    <thead className="bg-[var(--ink-card)] text-[var(--ink-meta)] uppercase text-[10px] font-bold tracking-wider">
                        <tr>
                            <th className="px-4 py-3">ID</th>
                            <th className="px-4 py-3">Content Preview</th>
                            <th className="px-4 py-3">Source File</th>
                            <th className="px-4 py-3">Tokens</th>
                            <th className="px-4 py-3">Status</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--ink-border)] bg-white">
                        {loading ? (
                            <tr>
                                <td colSpan={5} className="py-12 text-center">
                                    <div className="flex justify-center">
                                        <Loader2 size={24} className="animate-spin text-[var(--ink-meta)]" />
                                    </div>
                                </td>
                            </tr>
                        ) : chunks.map((chunk) => (
                            <tr key={chunk.id} className="hover:bg-[var(--ink-page)] transition-colors">
                                <td className="px-4 py-3 font-mono text-xs text-[var(--ink-meta)] max-w-[120px] truncate" title={chunk.id}>
                                    {chunk.id.split('-').pop()}
                                </td>
                                <td className="px-4 py-3 max-w-[300px]">
                                    <p className="truncate text-[var(--ink-body)]" title={chunk.content_preview}>
                                        {chunk.content_preview}
                                    </p>
                                </td>
                                <td className="px-4 py-3 text-[var(--ink-body)] flex items-center gap-1.5">
                                    <FileText size={12} className="text-[var(--ink-heading)]" />
                                    <span className="truncate max-w-[150px]">{chunk.source_file}</span>
                                </td>
                                <td className="px-4 py-3 font-mono text-xs text-[var(--ink-meta)]">
                                    {chunk.token_count}
                                </td>
                                <td className="px-4 py-3">
                                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${chunk.embedding_status === 'completed'
                                        ? 'bg-transparent border-black text-black'
                                        : 'bg-[var(--ink-border)]/20 border-[var(--ink-border)] text-[var(--ink-meta)]'
                                        }`}>
                                        <Database size={10} />
                                        {chunk.embedding_status}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            <div className="flex justify-between items-center text-xs text-[var(--ink-meta)]">
                <span>Showing {chunks.length} of {total} results</span>
                <div className="flex gap-1">
                    <button
                        disabled={page === 1}
                        onClick={() => setPage(p => p - 1)}
                        className="px-2 py-1 rounded border border-[var(--ink-border)] hover:bg-[var(--ink-card)] disabled:opacity-50"
                    >
                        Prev
                    </button>
                    <span className="px-2 py-1 bg-[var(--ink-card)] rounded">{page}</span>
                    <button
                        disabled={page * pageSize >= total}
                        onClick={() => setPage(p => p + 1)}
                        className="px-2 py-1 rounded border border-[var(--ink-border)] hover:bg-[var(--ink-card)] disabled:opacity-50"
                    >
                        Next
                    </button>
                </div>
            </div>
        </div>
    );
}
