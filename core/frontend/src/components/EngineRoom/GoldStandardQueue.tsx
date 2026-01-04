import React, { useState, useEffect } from 'react';
import { Check, X, Database, MessageSquare } from 'lucide-react';
import { cortexGet, cortexPost } from '@/utils/cortexApi';
import showToast from '@/utils/toast';

export const GoldStandardQueue = () => {
    const [samples, setSamples] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchSamples = async () => {
        setLoading(true);
        try {
            const data = await cortexGet<any[]>('/api/v1/evaluation/gold-standard/pending');
            setSamples(data || []);
        } catch (error) {
            console.error(error);
            setSamples([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSamples();
    }, []);

    const handleAction = async (id: string, action: 'VERIFIED' | 'REJECTED') => {
        try {
            await cortexPost(`/api/v1/evaluation/gold-standard/${id}/verify`, { action });
            showToast(action === 'VERIFIED' ? 'Sample Verified' : 'Sample Rejected', 'success');
            // Optimistic update
            setSamples(prev => prev.filter((s: any) => s.id !== id));
        } catch (error) {
            showToast('Action failed', 'error');
        }
    };

    if (loading) return <div className="text-slate-400 p-4">Loading verification queue...</div>;
    if (samples.length === 0) return <div className="text-slate-500 p-4 italic">No pending samples for verification. Good job!</div>;

    return (
        <div className="space-y-4">
            {samples.map((sample: any) => (
                <div key={sample.id} className="p-4 rounded-lg border border-[var(--ink-border)] bg-white shadow-sm hover:shadow-[4px_4px_0px_0px_var(--ink-shadow)] transition-all">
                    <div className="flex justify-between items-start gap-4">
                        <div className="flex-1 space-y-2">
                            <div className="flex items-start gap-2">
                                <MessageSquare size={16} className="text-[var(--ink-muted)] mt-1 shrink-0" />
                                <div>
                                    <div className="text-[10px] font-bold text-[var(--ink-muted)] uppercase">Query</div>
                                    <div className="text-sm text-[var(--ink-primary)] font-medium">{sample.query}</div>
                                </div>
                            </div>

                            <div className="pl-6 border-l-2 border-[var(--ink-border)] ml-2">
                                <div className="text-[10px] font-bold text-[var(--ink-muted)] uppercase">Response</div>
                                <div className="text-sm text-[var(--ink-primary)] leading-relaxed">{sample.response}</div>
                            </div>

                            <div className="flex items-center gap-2 pt-2">
                                <Database size={14} className="text-blue-600" />
                                <span className="text-xs text-[var(--ink-muted)]">
                                    {sample.context_chunks.length} Context Chunks
                                </span>
                            </div>
                        </div>

                        <div className="flex flex-col gap-2">
                            <button
                                onClick={() => handleAction(sample.id, 'VERIFIED')}
                                className="p-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-600 rounded-lg border border-emerald-200 transition-colors"
                                title="Approve as Gold Standard"
                            >
                                <Check size={18} />
                            </button>
                            <button
                                onClick={() => handleAction(sample.id, 'REJECTED')}
                                className="p-2 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg border border-red-200 transition-colors"
                                title="Reject (Hallucinated/Irrelevant)"
                            >
                                <X size={18} />
                            </button>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
};
