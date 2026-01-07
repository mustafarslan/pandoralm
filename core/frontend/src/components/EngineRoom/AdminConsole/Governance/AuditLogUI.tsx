
import React, { useState, useEffect } from 'react';
import { Search, Loader2, RefreshCw, FileText, User } from 'lucide-react';
import Audit from '@/models/audit';
import Workspace from '@/models/workspace';
import showToast from '@/utils/toast';

export default function AuditLogUI() {
    const [loading, setLoading] = useState(false);
    const [workspaces, setWorkspaces] = useState<any[]>([]);
    const [workspaceId, setWorkspaceId] = useState<string>('');

    const [logs, setLogs] = useState<any[]>([]);
    const [page, setPage] = useState(1);
    const [pageSize] = useState(50);

    // Fetch Workspaces on mount
    useEffect(() => {
        const fetchWorkspaces = async () => {
            const ws = await Workspace.all();
            if (ws && ws.length > 0) {
                setWorkspaces(ws);
                setWorkspaceId(ws[0].slug); // Default to first workspace
            }
        };
        fetchWorkspaces();
    }, []);

    const fetchLogs = async () => {
        if (!workspaceId) return;

        setLoading(true);
        try {
            const res = await Audit.getLogs(workspaceId, {}, pageSize, (page - 1) * pageSize);
            setLogs(res || []);
        } catch (e) {
            console.error(e);
            showToast("Failed to fetch audit logs", "error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs();
    }, [workspaceId, page]);

    return (
        <div className="p-4 space-y-4">
            <div className="flex justify-between items-center">
                <div>
                    <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Audit & Governance</h3>
                    <p className="text-sm text-[var(--ink-meta)]">
                        Track access, ingestion, and modifications for compliance.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <select
                        value={workspaceId}
                        onChange={(e) => setWorkspaceId(e.target.value)}
                        className="px-3 py-1.5 text-sm rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-violet-500/20"
                    >
                        {workspaces.map((ws) => (
                            <option key={ws.slug} value={ws.slug}>
                                {ws.name}
                            </option>
                        ))}
                    </select>
                    <button
                        onClick={fetchLogs}
                        disabled={loading}
                        className="p-2 text-[var(--ink-meta)] hover:text-[var(--ink-heading)] hover:bg-[var(--ink-border)]/50 rounded-lg transition-colors"
                        title="Refresh"
                    >
                        <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                    </button>
                </div>
            </div>

            {/* Data Table */}
            <div className="overflow-x-auto border border-[var(--ink-border)] rounded-lg">
                <table className="w-full text-sm text-left">
                    <thead className="bg-[var(--ink-card)] text-[var(--ink-meta)] uppercase text-[10px] font-bold tracking-wider">
                        <tr>
                            <th className="px-4 py-3">Timestamp</th>
                            <th className="px-4 py-3">User</th>
                            <th className="px-4 py-3">Action</th>
                            <th className="px-4 py-3">Resource</th>
                            <th className="px-4 py-3">Details</th>
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
                        ) : logs.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="py-8 text-center text-[var(--ink-meta)]">
                                    No audit logs found for this workspace.
                                </td>
                            </tr>
                        ) : logs.map((log) => (
                            <tr key={log.id} className="hover:bg-[var(--ink-page)] transition-colors">
                                <td className="px-4 py-3 font-mono text-xs text-[var(--ink-meta)]">
                                    {new Date(log.timestamp).toLocaleString()}
                                </td>
                                <td className="px-4 py-3 text-[var(--ink-body)] flex items-center gap-1.5">
                                    <User size={12} className="text-[var(--ink-meta)]" />
                                    {log.user_id}
                                </td>
                                <td className="px-4 py-3">
                                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border bg-[var(--ink-border)]/20 border-[var(--ink-border)] text-[var(--ink-heading)]">
                                        {log.action}
                                    </span>
                                </td>
                                <td className="px-4 py-3 text-[var(--ink-body)]">
                                    {log.resource_type && (
                                        <span className="text-[10px] text-[var(--ink-meta)] uppercase mr-1">{log.resource_type}:</span>
                                    )}
                                    {log.resource_id}
                                </td>
                                <td className="px-4 py-3 text-xs text-[var(--ink-meta)] max-w-[200px] truncate">
                                    {JSON.stringify(log.details)}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Pagination (Simple) */}
            <div className="flex justify-between items-center text-xs text-[var(--ink-meta)]">
                <span>Page {page}</span>
                <div className="flex gap-1">
                    <button
                        disabled={page === 1}
                        onClick={() => setPage(p => p - 1)}
                        className="px-2 py-1 rounded border border-[var(--ink-border)] hover:bg-[var(--ink-card)] disabled:opacity-50"
                    >
                        Prev
                    </button>
                    <button
                        disabled={logs.length < pageSize}
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
