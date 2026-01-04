import React from 'react';
import { ShieldCheck, Info, AlertTriangle } from 'lucide-react';

export const MetricGauge = ({ label, score, reason, threshold }) => {
    const isPassing = score >= threshold;
    // Determine color based on pass/fail
    const statusColor = isPassing ? 'text-os-fast' : 'text-red-500';
    const bgColor = isPassing ? 'bg-os-fast' : 'bg-red-500';
    const bgSoft = isPassing ? 'bg-os-fast/10' : 'bg-red-500/10';

    return (
        <div className="p-4 rounded-lg border border-[var(--ink-border)] bg-white shadow-[4px_4px_0px_0px_var(--ink-shadow)] flex flex-col h-full">
            <div className="flex justify-between items-start mb-3">
                <div>
                    <h4 className="text-[10px] font-bold text-[var(--ink-meta)] uppercase tracking-widest">{label}</h4>
                    <div className="text-3xl font-bold font-mono text-[var(--ink-heading)] mt-1">{(score * 100).toFixed(0)}%</div>
                </div>
                <div className={`p-2 rounded-lg ${bgSoft}`}>
                    {isPassing ? (
                        <ShieldCheck className={statusColor} size={20} />
                    ) : (
                        <AlertTriangle className={statusColor} size={20} />
                    )}
                </div>
            </div>

            <div className="flex items-center justify-between text-[10px] text-[var(--ink-muted)] mb-1 uppercase font-mono">
                <span>Score</span>
                <span>Target: &gt;{(threshold * 100).toFixed(0)}%</span>
            </div>

            {/* Visual Progress Bar */}
            <div className="h-1.5 w-full bg-[var(--ink-border)] rounded-full overflow-hidden mb-4">
                <div
                    className={`h-full transition-all duration-1000 ${bgColor}`}
                    style={{ width: `${score * 100}%` }}
                />
            </div>

            {/* DeepEval Reasoning */}
            <div className="mt-auto pt-3 border-t border-[var(--ink-border)]">
                <div className="flex gap-2 items-start group">
                    <Info size={14} className="text-[var(--ink-muted)] shrink-0 mt-0.5" />
                    <p className="text-xs text-[var(--ink-muted)] leading-relaxed italic line-clamp-3 group-hover:line-clamp-none transition-all">
                        "{reason}"
                    </p>
                </div>
            </div>
        </div>
    );
};
