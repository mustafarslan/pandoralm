import React, { useState, useEffect } from 'react';
import { Cpu, Activity, Database, AlertCircle, RefreshCw, Power } from 'lucide-react';
import System from '@/models/system';

export const WorkerHUD = () => {
    const [stats, setStats] = useState({
        gpu_active: 0,
        gpu_max: 8, // KEDA max replicas (static for now)
        latency_ms: 0,
        current_table: 'vectors',
        queue_depth: 0
    });

    const [isMigrating, setIsMigrating] = useState(false);

    useEffect(() => {
        const fetchWorkerStats = async () => {
            const data = await System.getWorkerStats();
            // Resilience: Only update if we get valid data. 
            // If backend returns "unknown" table (error state), keep showing old data (stale-while-revalidate)
            if (data && data.active_table !== 'unknown') {
                setStats({
                    gpu_active: data.worker_count || (data.queue_stats?.heavy_lifting || 0), // Prefer confirmed k8s pod count
                    gpu_max: 8,
                    latency_ms: data.api_latency_ms || 0,
                    current_table: data.active_table || 'vectors',
                    queue_depth: Object.values(data.queue_stats || {}).reduce((a: any, b: any) => a + b, 0) as number
                });
            }
        };

        fetchWorkerStats();
        const interval = setInterval(fetchWorkerStats, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, []);

    const handleBlueGreenSwitch = async () => {
        if (!confirm('WARNING: This will trigger a rolling restart and switch the active LanceDB table. Proceed?')) return;

        setIsMigrating(true);
        // Toggle between vectors and vectors_v2
        const targetTable = stats.current_table === 'vectors' ? 'vectors_v2' : 'vectors';

        const result = await System.switchTable(targetTable);

        if (result && !result.error) {
            setStats(prev => ({
                ...prev,
                current_table: targetTable
            }));
        } else {
            alert("Migration failed: " + (result?.error || "Unknown error"));
        }

        setIsMigrating(false);
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-6">
            {/* GPU Worker (Heavy Lifting) */}
            <div className="p-6 rounded-lg bg-white border border-[var(--ink-border)] shadow-[4px_4px_0px_0px_var(--ink-shadow)] relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-2 opacity-50 group-hover:opacity-100 transition-opacity">
                    <Power size={14} className="text-[var(--ink-muted)]" />
                </div>

                <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center gap-2">
                        <Cpu className="text-[var(--ink-primary)] w-5 h-5" />
                        <span className="text-sm font-bold text-[var(--ink-primary)] uppercase tracking-wider">GPU Node</span>
                    </div>
                </div>
                <div className="flex items-baseline gap-2">
                    <div className="text-3xl font-mono font-bold text-[var(--ink-heading)]">{stats.gpu_active}</div>
                    <div className="text-sm text-[var(--ink-meta)]">/ {stats.gpu_max} pods</div>
                </div>

                <div className="mt-3 h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
                    <div
                        className="h-full bg-[var(--ink-primary)] transition-all duration-1000 relative"
                        style={{ width: `${(stats.gpu_active / stats.gpu_max) * 100}%` }}
                    >
                    </div>
                </div>
                <p className="text-[10px] text-[var(--ink-meta)] mt-2 uppercase flex justify-between">
                    <span>KEDA Autoscaling</span>
                    <span className="text-[var(--ink-primary)] font-bold">{stats.queue_depth > 0 ? 'SCALING UP' : 'IDLE'}</span>
                </p>
            </div>

            {/* API Context Latency */}
            <div className="p-6 rounded-lg bg-white border border-[var(--ink-border)] shadow-[4px_4px_0px_0px_var(--ink-shadow)]">
                <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center gap-2">
                        <Activity className="text-[var(--ink-primary)] w-5 h-5" />
                        <span className="text-sm font-bold text-[var(--ink-primary)] uppercase tracking-wider">System Latency</span>
                    </div>
                </div>
                <div className="text-3xl font-mono font-bold text-[var(--ink-heading)]">{stats.latency_ms}<span className="text-sm font-normal text-[var(--ink-meta)] ml-1">ms</span></div>
                <div className="mt-2 text-[10px] text-[var(--ink-meta)] uppercase flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                    Semantic Router Active
                </div>
            </div>

            {/* Vector Table Sync (Blue/Green) */}
            <div className="p-6 rounded-lg bg-white border border-[var(--ink-border)] shadow-[4px_4px_0px_0px_var(--ink-shadow)] flex flex-col justify-between">
                <div>
                    <div className="flex justify-between items-center mb-4">
                        <div className="flex items-center gap-2">
                            <Database className="text-[var(--ink-primary)] w-5 h-5" />
                            <span className="text-sm font-bold text-[var(--ink-primary)] uppercase tracking-wider">LanceDB Sync</span>
                        </div>
                    </div>
                    <div className="flex justify-between items-end">
                        <div>
                            <div className="text-sm font-mono text-[var(--ink-meta)] mb-1">active_table:</div>
                            <div className="text-lg font-bold text-[var(--ink-heading)] font-mono bg-gray-100 px-2 py-1 rounded border border-gray-300 inline-block">
                                {stats.current_table}
                            </div>
                        </div>

                        <button
                            onClick={handleBlueGreenSwitch}
                            disabled={isMigrating}
                            className={`
                                p-2 rounded-lg border transition-all
                                ${isMigrating
                                    ? 'bg-amber-50 border-amber-200 text-amber-600 cursor-wait'
                                    : 'bg-gray-50 hover:bg-gray-100 border-gray-200 hover:border-gray-300 text-gray-500 hover:text-black'}
                            `}
                            title="Switch Active Table (Blue/Green)"
                        >
                            <RefreshCw size={16} className={isMigrating ? 'animate-spin' : ''} />
                        </button>
                    </div>
                </div>

                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-[var(--ink-border)]/20 justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-emerald-500" />
                        <span className="text-[10px] text-emerald-600 font-bold uppercase tracking-widest">S3 CONNECTED</span>
                    </div>

                    <button
                        onClick={async () => {
                            if (confirm('Rebuild knowledge graph for ALL workspaces? This is a heavy operation.')) {
                                await System.rebuildGraph();
                                alert('Graph rebuild queued.');
                            }
                        }}
                        className="text-[10px] text-[var(--ink-primary)] hover:underline uppercase font-bold tracking-wider"
                    >
                        Rebuild Graphs
                    </button>
                </div>
            </div>
        </div>
    );
};

export default WorkerHUD;
