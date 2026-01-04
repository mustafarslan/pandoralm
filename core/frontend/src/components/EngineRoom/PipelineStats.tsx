import React, { useState, useEffect } from 'react';
import { FileText, ArrowRight, Database, Network, CheckCircle2, Loader2, GitBranch, XCircle, Info } from 'lucide-react';
import System from '@/models/system';
import { HelpTooltip } from '@/components/HelpTooltip';

interface TaskStage {
    id: string;
    stage: 'DOC_EXTRACT' | 'VECTOR_READY' | 'GRAPH_COMPLETE';
    filename: string;
    progress: number;
    status: 'processing' | 'completed' | 'failed' | 'queued';
    layer: string;
}

export const PipelineStats = () => {
    // Mock data for initial UI
    // Real-time Pipeline Metrics
    const [tasks, setTasks] = useState<TaskStage[]>([]);
    const [metrics, setMetrics] = useState<any>({});

    const fetchPipelineStats = async () => {
        const jobsData = await System.listActiveJobs();
        const statsData = await System.getWorkerStats();

        // Resilience: Check if pipeline_stats exists AND has valid data (not empty fallback obj)
        if (statsData?.pipeline_stats?.vector_ready) setMetrics(statsData);

        if (jobsData?.jobs) {
            const mappedTasks: TaskStage[] = jobsData.jobs.map((job: any) => {
                let stage: TaskStage['stage'] = 'DOC_EXTRACT';
                if (job.task_name.includes('vector')) stage = 'VECTOR_READY';
                if (job.task_name.includes('graph')) stage = 'GRAPH_COMPLETE';

                // Try to guess filename from args or direct property
                const filename = job.filename || (Array.isArray(job.args) && job.args[0]
                    ? (typeof job.args[0] === 'string' ? job.args[0].split('/').pop() : 'Unknown File')
                    : 'Unknown Job');

                return {
                    id: job.job_id,
                    stage,
                    filename,
                    progress: job.status === 'running' ? 50 : 0,
                    status: job.status === 'running' ? 'processing' : 'queued',
                    layer: 'system' // Default as we can't easily parse layer from args yet
                };
            });
            setTasks(mappedTasks);
        }
    };

    const handleCancel = async (taskId: string) => {
        if (!window.confirm("Are you sure you want to stop this job?")) return;
        const res = await System.revokeJob(taskId);
        if (res) fetchPipelineStats();
    };

    useEffect(() => {
        fetchPipelineStats();
        const interval = setInterval(fetchPipelineStats, 15000);
        return () => clearInterval(interval);
    }, []);

    // Pipeline visualization component
    const PipelineNode = ({ label, icon: Icon, active, completed, count }: any) => (
        <div className={`relative flex flex-col items-center p-4 rounded-xl border transition-all w-32
            ${active
                ? 'bg-white border-2 border-black text-black shadow-lg font-bold'
                : completed
                    ? 'bg-white border border-black text-black'
                    : 'bg-white border border-neutral-200 text-neutral-400'}
        `}>
            {count > 0 && (
                <div className="absolute -top-3 -right-3 h-6 min-w-[1.5rem] px-1.5 rounded-full bg-black text-white border-2 border-white text-[10px] font-bold flex items-center justify-center shadow-lg z-10">
                    {count.toLocaleString()}
                </div>
            )}
            <Icon size={20} className={`mb-2 ${active || completed ? 'text-black' : 'text-neutral-400'}`} />
            <span className={`text-[10px] font-bold uppercase ${active || completed ? 'text-black' : 'text-neutral-400'}`}>{label}</span>
        </div>
    );

    const PipelineConnector = ({ active }: { active: boolean }) => (
        <div className="flex-1 h-[2px] mx-2 relative">
            <div className="absolute inset-x-0 h-full bg-os-border"></div>
            {active && (
                <div className="absolute inset-x-0 h-full bg-os-code animate-shimmer">
                    <div className="absolute right-0 -top-1 w-2 h-2 rotate-45 border-t-2 border-r-2 border-os-code"></div>
                </div>
            )}
        </div>
    );

    return (
        <div className="bg-os-bg border-t border-os-border">

            {/* Visual Flow */}
            {/* Visual Flow - Powered by Real Metrics */}
            <div className="flex items-center justify-between mb-8 px-8">
                <PipelineNode
                    label="Extract"
                    icon={FileText}
                    completed={true}
                    count={0} // Core handles this, usually transient
                />
                <PipelineConnector active={true} />
                <PipelineNode
                    label="Vectorize"
                    icon={Database}
                    active={true}
                    count={metrics.pipeline_stats?.vector_ready?.count || 0}
                />
                <PipelineConnector active={true} />
                <PipelineNode
                    label="Graph Index"
                    icon={Network}
                    active={true}
                    count={metrics.pipeline_stats?.graph_index?.count || 0}
                />
            </div>

            {/* Recent Tasks Table */}
            <div className="ink-table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Task ID</th>
                            <th>File</th>
                            <th>Layer</th>
                            <th>Phase</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tasks.map((task) => (
                            <tr key={task.id}>
                                <td className="font-mono text-xs">{task.id}</td>
                                <td title={task.filename} className="max-w-[150px]">
                                    <div className="flex items-center gap-1 group relative cursor-help">
                                        <span className="truncate">{task.filename}</span>
                                        {task.filename.length > 20 && (
                                            <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block z-50 p-2 bg-black text-white text-xs rounded shadow-lg whitespace-nowrap">
                                                {task.filename}
                                                <div className="absolute top-full left-4 -mt-1 border-4 border-transparent border-t-black"></div>
                                            </div>
                                        )}
                                    </div>
                                </td>
                                <td>
                                    <span className="ink-badge neutral font-mono">
                                        {task.layer}
                                    </span>
                                </td>
                                <td>
                                    <div className="flex items-center gap-2">
                                        <div className="w-16 h-1.5 bg-ink-panel rounded-full overflow-hidden">
                                            <div
                                                className={`h-full rounded-full ${task.stage === 'GRAPH_COMPLETE' ? 'bg-os-heavy' : 'bg-os-code'}`}
                                                style={{ width: `${task.progress}%` }}
                                            />
                                        </div>
                                        <span className="text-[10px] text-ink-muted font-bold uppercase">{task.stage.replace('_', ' ')}</span>
                                    </div>
                                </td>
                                <td>
                                    {task.status === 'processing' ? (
                                        <span className="ink-badge warning">
                                            <span className="ink-badge-dot bg-amber-500 animate-pulse"></span> Processing
                                        </span>
                                    ) : task.status === 'completed' ? (
                                        <span className="ink-badge success">
                                            <span className="ink-badge-dot bg-emerald-500"></span> Done
                                        </span>
                                    ) : (
                                        <span className="ink-badge neutral capitalize">{task.status}</span>
                                    )}
                                </td>
                                <td>
                                    {(task.status === 'processing' || task.status === 'queued') && (
                                        <button
                                            onClick={() => handleCancel(task.id)}
                                            className="text-red-500 hover:text-red-700 transition-colors p-1"
                                            title="Stop Job"
                                        >
                                            <XCircle size={14} />
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default PipelineStats;
