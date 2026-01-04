import React, { useState, useEffect, useCallback } from 'react';
import { Activity, Shield, Target, AlertTriangle, Download, RefreshCw, Bell } from 'lucide-react';
import MetricGauge from './MetricGauge';
import { cortexFetch, CORTEX_API } from '@/utils/cortexApi';

interface QualityMetrics {
    faithfulness: number;
    answerRelevancy: number;
    contextPrecision: number;
    hallucinationRate: number;
    lastUpdated: string;
}

interface EvalResult {
    id: string;
    query: string;
    faithfulness: number;
    relevancy: number;
    passed: boolean;
    timestamp: string;
}

/**
 * QualityGateDashboard - Main dashboard for RAG evaluation metrics
 * 
 * Part of the Quality Gate HUD (UI Phase 5).
 * Shows live metrics, regression history, and gold standard management.
 * Connects to Cortex `/api/v1/eval/metrics` with fallback to mock data.
 */
export const QualityGateDashboard: React.FC = () => {
    const [metrics, setMetrics] = useState<QualityMetrics | null>(null);
    const [recentEvals, setRecentEvals] = useState<EvalResult[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [regressionAlert, setRegressionAlert] = useState<string | null>(null);
    const [goldStandardCount, setGoldStandardCount] = useState(42);

    // Fetch metrics from Cortex API
    const fetchMetrics = useCallback(async () => {
        setIsLoading(true);
        try {
            // Try to fetch from real Cortex endpoint
            const response = await cortexFetch('/api/v1/eval/metrics');

            if (response.ok) {
                const data = await response.json();
                const fetchedMetrics: QualityMetrics = {
                    faithfulness: data.faithfulness || 0,
                    answerRelevancy: data.answer_relevancy || data.answerRelevancy || 0,
                    contextPrecision: data.context_precision || data.contextPrecision || 0,
                    hallucinationRate: data.hallucination_rate || data.hallucinationRate || 0,
                    lastUpdated: data.last_updated || new Date().toISOString()
                };

                setMetrics(fetchedMetrics);
                setRecentEvals(data.recent_evals || data.recentEvals || []);
                setGoldStandardCount(data.golden_dataset_count || 42);

                // Check for regression alert (Faithfulness < 0.8)
                if (fetchedMetrics.faithfulness < 0.8) {
                    setRegressionAlert(`Faithfulness score (${(fetchedMetrics.faithfulness * 100).toFixed(0)}%) is below threshold (80%)!`);
                } else {
                    setRegressionAlert(null);
                }

                setError(null);
            } else {
                // Fallback to mock data
                loadMockData();
            }
        } catch (err) {
            console.warn('[QualityGate] Falling back to mock data:', err);
            loadMockData();
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Mock data for development/demo
    const loadMockData = () => {
        const mockMetrics: QualityMetrics = {
            faithfulness: 0.87,
            answerRelevancy: 0.82,
            contextPrecision: 0.79,
            hallucinationRate: 0.05,
            lastUpdated: new Date().toISOString()
        };

        const mockEvals: EvalResult[] = [
            { id: '1', query: "What is the company policy on remote work?", faithfulness: 0.92, relevancy: 0.88, passed: true, timestamp: new Date().toISOString() },
            { id: '2', query: "Summarize the Q3 financial report", faithfulness: 0.85, relevancy: 0.78, passed: true, timestamp: new Date().toISOString() },
            { id: '3', query: "How does authentication work?", faithfulness: 0.76, relevancy: 0.81, passed: false, timestamp: new Date().toISOString() },
        ];

        setMetrics(mockMetrics);
        setRecentEvals(mockEvals);

        // Check mock data for regression
        if (mockMetrics.faithfulness < 0.8) {
            setRegressionAlert(`Faithfulness score (${(mockMetrics.faithfulness * 100).toFixed(0)}%) is below threshold (80%)!`);
        }
    };

    useEffect(() => {
        fetchMetrics();
    }, [fetchMetrics]);

    // Handler for saving response to gold standard
    const handleSaveToGoldStandard = async (evalId: string) => {
        try {
            const response = await cortexFetch('/api/v1/eval/golden-dataset', {
                method: 'POST',
                body: JSON.stringify({ eval_id: evalId }),
            });

            if (response.ok) {
                setGoldStandardCount(prev => prev + 1);
            }
        } catch (err) {
            console.error('[QualityGate] Failed to save to gold standard:', err);
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-os-heavy" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Regression Alert Banner */}
            {regressionAlert && (
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 flex items-center gap-3 animate-pulse">
                    <Bell className="w-5 h-5 flex-shrink-0" />
                    <div className="flex-1">
                        <h4 className="font-bold text-sm">Regression Alert</h4>
                        <p className="text-xs">{regressionAlert}</p>
                    </div>
                    <button
                        onClick={() => setRegressionAlert(null)}
                        className="text-red-400 hover:text-red-300 text-sm"
                    >
                        Dismiss
                    </button>
                </div>
            )}

            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <Shield className="w-5 h-5 text-os-heavy" />
                        Quality Gate HUD
                    </h2>
                    <p className="text-sm text-slate-500 mt-1">
                        RAG performance metrics from DeepEval
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={fetchMetrics}
                        className="px-3 py-1.5 rounded-lg bg-os-surface border border-os-border text-slate-300 hover:bg-os-surface/80 transition-colors flex items-center gap-2 text-sm"
                    >
                        <RefreshCw className="w-4 h-4" />
                        Refresh
                    </button>
                    <button className="px-3 py-1.5 rounded-lg bg-os-heavy/20 border border-os-heavy/30 text-os-heavy hover:bg-os-heavy/30 transition-colors flex items-center gap-2 text-sm">
                        <Download className="w-4 h-4" />
                        Export Report
                    </button>
                </div>
            </div>

            {/* Error Banner */}
            {error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    {error}
                </div>
            )}

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricGauge
                    label="Faithfulness"
                    score={metrics?.faithfulness || 0}
                    threshold={0.8}
                    reason="Measures factual consistency with retrieved context. Target: >80%"
                    trend="up"
                />
                <MetricGauge
                    label="Answer Relevancy"
                    score={metrics?.answerRelevancy || 0}
                    threshold={0.7}
                    reason="Quantifies how well the response addresses the query. Target: >70%"
                    trend="stable"
                />
                <MetricGauge
                    label="Context Precision"
                    score={metrics?.contextPrecision || 0}
                    threshold={0.75}
                    reason="Validates if LanceDB retriever ranks relevant chunks correctly."
                />
                <div className="p-4 rounded-xl border border-os-border bg-os-surface/40">
                    <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                        Hallucination Rate
                    </h4>
                    <div className="text-2xl font-bold text-white">
                        {((metrics?.hallucinationRate || 0) * 100).toFixed(1)}%
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">
                        Lower is better. Target: &lt;10%
                    </p>
                </div>
            </div>

            {/* Recent Evaluations with Save to Gold Standard */}
            <div className="border border-os-border rounded-xl bg-os-surface/20">
                <div className="p-4 border-b border-os-border">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <Activity className="w-4 h-4 text-os-code" />
                        Recent Evaluations
                    </h3>
                </div>
                <div className="divide-y divide-os-border">
                    {recentEvals.map((eval_) => (
                        <div key={eval_.id} className="p-4 flex items-center justify-between hover:bg-os-surface/30 transition-colors group">
                            <div className="flex-1 min-w-0">
                                <p className="text-sm text-slate-200 truncate">{eval_.query}</p>
                                <div className="flex items-center gap-4 mt-1">
                                    <span className="text-[10px] text-slate-500">
                                        Faith: {(eval_.faithfulness * 100).toFixed(0)}%
                                    </span>
                                    <span className="text-[10px] text-slate-500">
                                        Rel: {(eval_.relevancy * 100).toFixed(0)}%
                                    </span>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                {/* Save to Gold Standard button */}
                                <button
                                    onClick={() => handleSaveToGoldStandard(eval_.id)}
                                    className="opacity-0 group-hover:opacity-100 px-2 py-1 rounded text-[10px] font-medium bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30 transition-all"
                                    title="Save to Gold Standard"
                                >
                                    Save ⭐
                                </button>
                                <div className={`px-2 py-0.5 rounded text-[10px] font-bold ${eval_.passed
                                    ? 'bg-os-fast/20 text-os-fast'
                                    : 'bg-red-500/20 text-red-400'
                                    }`}>
                                    {eval_.passed ? 'PASS' : 'FAIL'}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Gold Standard Section */}
            <div className="border border-os-border rounded-xl bg-os-surface/20 p-4">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <Target className="w-4 h-4 text-yellow-500" />
                        Gold Standard Dataset
                    </h3>
                    <span className="text-[10px] text-slate-500 bg-os-surface px-2 py-1 rounded">
                        {goldStandardCount} entries
                    </span>
                </div>
                <p className="text-sm text-slate-400 mb-4">
                    High-quality Q/A pairs used for CI/CD regression testing
                </p>
                <div className="flex gap-2">
                    <button className="px-3 py-1.5 rounded-lg bg-os-surface border border-os-border text-slate-300 hover:bg-os-surface/80 transition-colors text-sm">
                        Generate Synthetic Data
                    </button>
                    <button className="px-3 py-1.5 rounded-lg bg-os-surface border border-os-border text-slate-300 hover:bg-os-surface/80 transition-colors text-sm">
                        View Verification Queue
                    </button>
                </div>
            </div>
        </div>
    );
};

export default QualityGateDashboard;
