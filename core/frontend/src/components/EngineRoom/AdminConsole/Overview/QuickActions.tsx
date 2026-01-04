import React, { useState } from 'react';
import { RefreshCw, Database, Layers, ArrowLeftRight } from 'lucide-react';
import { cortexPost } from '@/utils/cortexApi';
import showToast from '@/utils/toast';

export default function QuickActions() {
    const [loading, setLoading] = useState<string | null>(null);

    const handleAction = async (action: string, endpoint: string, body: any = {}, successMessage: string) => {
        setLoading(action);
        try {
            await cortexPost(endpoint, body);
            showToast(successMessage, 'success');
        } catch (e) {
            console.error(e);
            showToast(`Action failed: ${e}`, 'error');
        } finally {
            setLoading(null);
        }
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Rebuild GraphRAG */}
            <button
                onClick={() => handleAction('rebuild_graph', '/api/v1/ops/graph/rebuild-all', {}, 'GraphRAG Rebuild Queued')}
                disabled={!!loading}
                className="p-4 rounded-xl border border-[var(--ink-border)] bg-[var(--ink-card)] hover:bg-[var(--ink-page)] transition-all text-left group"
            >
                <div className="flex justify-between items-start mb-2">
                    <Layers className="w-5 h-5 text-[var(--ink-heading)] group-hover:scale-110 transition-transform" />
                    {loading === 'rebuild_graph' && <RefreshCw className="w-4 h-4 animate-spin text-[var(--ink-meta)]" />}
                </div>
                <h4 className="text-sm font-bold text-[var(--ink-heading)]">Rebuild GraphRAG</h4>
                <p className="text-xs text-[var(--ink-meta)] mt-1">
                    Triggers full re-indexing of all documents into Neo4j.
                </p>
            </button>

            {/* Reindex Vectors */}
            <button
                onClick={() => handleAction('reindex_vectors', '/api/v1/ops/vectors/reindex-all', {}, 'Vector Re-indexing Queued')}
                disabled={!!loading}
                className="p-4 rounded-xl border border-[var(--ink-border)] bg-[var(--ink-card)] hover:bg-[var(--ink-page)] transition-all text-left group"
            >
                <div className="flex justify-between items-start mb-2">
                    <Database className="w-5 h-5 text-[var(--ink-heading)] group-hover:scale-110 transition-transform" />
                    {loading === 'reindex_vectors' && <RefreshCw className="w-4 h-4 animate-spin text-[var(--ink-meta)]" />}
                </div>
                <h4 className="text-sm font-bold text-[var(--ink-heading)]">Re-Embed Vectors</h4>
                <p className="text-xs text-[var(--ink-meta)] mt-1">
                    Re-runs embedding model on all text chunks.
                </p>
            </button>

            {/* Switch Blue/Green Table */}
            <button
                onClick={() => handleAction('switch_table', '/api/v1/ops/switch-table', { table_name: 'vectors_v2' }, 'Switched to Blue/Green Table')} // TODO: Make dynamic if needed
                disabled={!!loading}
                className="p-4 rounded-xl border border-[var(--ink-border)] bg-[var(--ink-card)] hover:bg-[var(--ink-page)] transition-all text-left group"
            >
                <div className="flex justify-between items-start mb-2">
                    <ArrowLeftRight className="w-5 h-5 text-[var(--ink-heading)] group-hover:scale-110 transition-transform" />
                    {loading === 'switch_table' && <RefreshCw className="w-4 h-4 animate-spin text-[var(--ink-meta)]" />}
                </div>
                <h4 className="text-sm font-bold text-[var(--ink-heading)]">Switch Vector Table</h4>
                <p className="text-xs text-[var(--ink-meta)] mt-1">
                    Toggle between Blue/Green LanceDB tables.
                </p>
            </button>
        </div>
    );
}
