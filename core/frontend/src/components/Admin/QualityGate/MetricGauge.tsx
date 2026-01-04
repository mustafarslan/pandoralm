import React from 'react';
import { ShieldCheck, Info, TrendingUp, TrendingDown } from 'lucide-react';

interface MetricGaugeProps {
    label: string;
    score: number;
    threshold: number;
    reason?: string;
    trend?: 'up' | 'down' | 'stable';
}

/**
 * MetricGauge - Visualizes a single RAG quality metric (Faithfulness, Relevancy, etc.)
 * 
 * Part of the Quality Gate HUD (UI Phase 5).
 * Shows pass/fail status based on threshold comparison.
 */
export const MetricGauge: React.FC<MetricGaugeProps> = ({
    label,
    score,
    threshold,
    reason,
    trend
}) => {
    const isPassing = score >= threshold;
    const percentage = Math.min(score * 100, 100);

    return (
        <div className="p-4 rounded-xl border border-os-border bg-os-surface/40 backdrop-blur-sm relative overflow-hidden">
            {/* Header */}
            <div className="flex justify-between items-start mb-3">
                <div>
                    <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                        {label}
                    </h4>
                    <div className="flex items-baseline gap-2 mt-1">
                        <span className="text-2xl font-bold text-white">
                            {percentage.toFixed(0)}%
                        </span>
                        <span className="text-[10px] text-slate-500">
                            / {(threshold * 100).toFixed(0)}% min
                        </span>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    {trend && trend !== 'stable' && (
                        <div className={`p-1 rounded ${trend === 'up' ? 'bg-os-fast/10' : 'bg-red-500/10'}`}>
                            {trend === 'up' ? (
                                <TrendingUp className="w-3 h-3 text-os-fast" />
                            ) : (
                                <TrendingDown className="w-3 h-3 text-red-500" />
                            )}
                        </div>
                    )}
                    <div className={`p-2 rounded-lg ${isPassing ? 'bg-os-fast/10' : 'bg-red-500/10'}`}>
                        <ShieldCheck className={`w-4 h-4 ${isPassing ? 'text-os-fast' : 'text-red-500'}`} />
                    </div>
                </div>
            </div>

            {/* Progress Bar */}
            <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                <div
                    className={`h-full transition-all duration-1000 ${isPassing ? 'bg-os-fast' : 'bg-red-500'}`}
                    style={{ width: `${percentage}%` }}
                />
            </div>

            {/* Threshold Marker */}
            <div
                className="absolute h-1.5 w-0.5 bg-slate-400"
                style={{ left: `${threshold * 100}%`, bottom: '16px' }}
            />

            {/* Reasoning (DeepEval explanation) */}
            {reason && (
                <div className="mt-3 flex gap-2 items-start group">
                    <Info size={12} className="text-slate-500 shrink-0 mt-0.5" />
                    <p className="text-[10px] text-slate-400 leading-tight italic line-clamp-2 group-hover:line-clamp-none transition-all">
                        {reason}
                    </p>
                </div>
            )}

            {/* Pass/Fail Badge */}
            <div className={`absolute top-3 right-3 px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider ${isPassing
                    ? 'bg-os-fast/20 text-os-fast border border-os-fast/30'
                    : 'bg-red-500/20 text-red-400 border border-red-500/30'
                }`}>
                {isPassing ? 'PASS' : 'FAIL'}
            </div>
        </div>
    );
};

export default MetricGauge;
