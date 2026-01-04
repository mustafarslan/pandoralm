import React, { useState, useEffect } from 'react';
import { Activity, Cpu, Server, Database } from 'lucide-react';
import { cortexGet } from '@/utils/cortexApi';

export default function SystemHealth() {
    const [stats, setStats] = useState<any>(null);

    useEffect(() => {
        const fetchHealth = async () => {
            try {
                const res = await cortexGet<any>('/api/v1/ops/health/overview');
                setStats(res);
            } catch (e) {
                console.error("Failed to fetch health stats", e);
                // Return zeroed state on error instead of fake data
                setStats({
                    api_latency_ms: 0,
                    queue_stats: { fast_lane: 0, heavy_lifting: 0 },
                    vector_stats: { total_chunks: 0, active_table: 'unknown' },
                    graph_connected: false
                });
            }
        };
        fetchHealth();

        const interval = setInterval(fetchHealth, 5000);
        return () => {
            clearInterval(interval);
        };
    }, []);

    if (!stats) return <div className="h-24 animate-pulse bg-[var(--ink-page)] border border-[var(--ink-border)] rounded-xl mb-6" />;

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="p-3 bg-[var(--ink-page)] rounded-lg border border-[var(--ink-border)]">
                <div className="flex items-center gap-2 mb-1 text-[var(--ink-meta)]">
                    <Activity size={14} />
                    <span className="text-xs font-bold uppercase">API Latency</span>
                </div>
                <div className="text-xl font-bold text-[var(--ink-heading)]">{stats.api_latency_ms}ms</div>
            </div>

            <div className="p-3 bg-[var(--ink-page)] rounded-lg border border-[var(--ink-border)]">
                <div className="flex items-center gap-2 mb-1 text-[var(--ink-meta)]">
                    <Cpu size={14} />
                    <span className="text-xs font-bold uppercase">Job Queues</span>
                </div>
                <div className="text-xl font-bold text-[var(--ink-heading)]">
                    {stats.queue_stats?.fast_lane + stats.queue_stats?.heavy_lifting || 0}
                </div>
                <div className="text-[10px] text-[var(--ink-meta)]">
                    Fast: {stats.queue_stats?.fast_lane} | Heavy: {stats.queue_stats?.heavy_lifting}
                </div>
            </div>

            <div className="p-3 bg-[var(--ink-page)] rounded-lg border border-[var(--ink-border)]">
                <div className="flex items-center gap-2 mb-1 text-[var(--ink-meta)]">
                    <Database size={14} />
                    <span className="text-xs font-bold uppercase">Vector Store</span>
                </div>
                <div className="text-xl font-bold text-[var(--ink-heading)]">
                    {(stats.vector_stats?.total_chunks || 0).toLocaleString()}
                </div>
                <div className="text-[10px] text-[var(--ink-meta)]">
                    Table: {stats.active_table || 'default'}
                </div>
            </div>

            <div className="p-3 bg-[var(--ink-page)] rounded-lg border border-[var(--ink-border)]">
                <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2 text-[var(--ink-meta)]">
                        <Server size={14} />
                        <span className="text-xs font-bold uppercase">Knowledge Graph</span>
                    </div>
                    <div className={`w-2 h-2 rounded-full ${stats.graph_connected ? 'bg-green-500' : 'bg-red-500'}`} title={stats.graph_connected ? "Online" : "Offline"} />
                </div>
                <div className="text-xl font-bold text-[var(--ink-heading)]">
                    {((stats.pipeline_stats?.graph_index?.count || 0)).toLocaleString()}
                    <span className="text-sm font-normal text-[var(--ink-muted)] ml-1">nodes</span>
                </div>
                <div className="text-[10px] text-[var(--ink-meta)]">
                    {(stats.pipeline_stats?.graph_index?.relationships || 0).toLocaleString()} relationships | {(stats.pipeline_stats?.graph_index?.communities || 0).toLocaleString()} communities
                </div>
            </div>
        </div>
    );
}
