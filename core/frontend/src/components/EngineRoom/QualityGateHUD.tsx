import React, { useState, useEffect } from 'react';
import { Activity, Shield, TrendingDown } from 'lucide-react';
import { MetricGauge } from './MetricGauge';
import { GoldStandardQueue } from './GoldStandardQueue';
import System from '@/models/system';

export const QualityGateHUD = () => {
    const [status, setStatus] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const data = await System.getQualityGateStatus();
                if (data) {
                    setStatus(data);
                }
            } catch (error) {
                console.error("Failed to load quality metrics", error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        // Poll every 30 seconds
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, []);

    if (loading) return <div className="text-slate-400 text-sm p-6">Loading Quality Metrics...</div>;
    if (!status) return <div className="text-red-400 text-sm p-6">Failed to load Quality Metrics. (Cortex Offline)</div>;

    return (
        <div className="flex flex-col gap-4">
            {/* Top Header Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 rounded-lg border border-[var(--ink-border)] bg-white shadow-[4px_4px_0px_0px_var(--ink-shadow)] flex items-center justify-between">
                    <div>
                        <div className="text-[10px] font-bold text-[var(--ink-muted)] uppercase">Quality Gate Status</div>
                        <div className={`text-2xl font-bold ${status.status === 'PASS' ? 'text-emerald-600' : 'text-red-600'}`}>
                            {status.status}
                        </div>
                    </div>
                    <Shield className={status.status === 'PASS' ? 'text-emerald-600' : 'text-red-600'} size={24} />
                </div>
                <div className="p-4 rounded-lg border border-[var(--ink-border)] bg-white shadow-[4px_4px_0px_0px_var(--ink-shadow)] flex items-center justify-between">
                    <div>
                        <div className="text-[10px] font-bold text-[var(--ink-muted)] uppercase">Last Run</div>
                        <div className="text-lg font-bold text-[var(--ink-primary)]">
                            {new Date(status.last_run).toLocaleTimeString()}
                        </div>
                    </div>
                    <Activity className="text-blue-600" size={24} />
                </div>
                <div className="p-4 rounded-lg border border-[var(--ink-border)] bg-white shadow-[4px_4px_0px_0px_var(--ink-shadow)]">
                    <div className="flex justify-between items-center mb-2">
                        <div className="text-[10px] font-bold text-[var(--ink-muted)] uppercase">Hallucination Rate Trend</div>
                        <TrendingDown className="text-emerald-600" size={16} />
                    </div>
                    {/* Simple Sparkline Representation */}
                    <div className="flex items-end gap-1 h-8">
                        {status.hallucination_rate_history.map((rate: number, idx: number) => (
                            <div
                                key={idx}
                                className="w-full bg-[var(--ink-muted)] rounded-sm hover:bg-emerald-600 transition-colors"
                                style={{ height: `${Math.max(rate * 500, 10)}%` }} // Scale for visibility
                                title={`Rate: ${(rate * 100).toFixed(1)}%`}
                            />
                        ))}
                    </div>
                </div>
            </div>

            {/* Metric Gauges Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 h-full">
                {status.metrics.map((metric: any) => (
                    <MetricGauge
                        key={metric.name}
                        label={metric.name}
                        score={metric.score}
                        threshold={metric.threshold}
                        reasoning={metric.reasoning}
                    />
                ))}
            </div>
            {/* Gold Standard Verification Queue */}
            <div className="mt-4">
                <div className="text-[10px] font-bold text-[var(--ink-muted)] uppercase mb-2">Gold Standard Verification Queue</div>
                <div className="bg-transparent pt-2">
                    <GoldStandardQueue />
                </div>
            </div>
        </div>
    );
};
