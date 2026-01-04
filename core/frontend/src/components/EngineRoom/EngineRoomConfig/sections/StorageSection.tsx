import React, { useState, useEffect } from 'react';
import { Database, FileText, MessageSquare, Save, Loader2 } from 'lucide-react';
import System from '@/models/system';
import showToast from '@/utils/toast';

type SubTab = 'vectordb' | 'splitter' | 'prompt';

export default function StorageSection() {
    const [activeSubTab, setActiveSubTab] = useState<SubTab>('vectordb');
    const [settings, setSettings] = useState<any>({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        async function fetchSettings() {
            try {
                const data = await System.keys();
                setSettings(data || {});
            } catch (e) {
                console.error('Failed to fetch settings:', e);
            } finally {
                setLoading(false);
            }
        }
        fetchSettings();
    }, []);

    const handleSave = async (updates: Record<string, any>) => {
        setSaving(true);
        try {
            const { newValues, error } = await System.updateSystem(updates);
            if (error) {
                showToast(`Error: ${error}`, 'error');
            } else {
                showToast('Settings saved successfully', 'success');
                setSettings((prev: any) => ({ ...prev, ...newValues }));
            }
        } catch (e) {
            showToast('Failed to save settings', 'error');
        } finally {
            setSaving(false);
        }
    };

    const subTabs = [
        { id: 'vectordb', label: 'Vector Database', icon: <Database size={16} /> },
        { id: 'splitter', label: 'Text Splitter', icon: <FileText size={16} /> },
        { id: 'prompt', label: 'System Prompt', icon: <MessageSquare size={16} /> },
    ];

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-[var(--ink-meta)]" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex gap-2 flex-wrap">
                {subTabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveSubTab(tab.id as SubTab)}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${activeSubTab === tab.id
                            ? 'bg-ink-action text-white shadow-sm'
                            : 'text-ink-muted hover:bg-ink-panel hover:text-ink-primary'
                            }`}
                    >
                        {tab.icon}
                        {tab.label}
                    </button>
                ))}
            </div>

            <div className="bg-[var(--ink-page)] rounded-lg border border-[var(--ink-border)] p-4">
                {activeSubTab === 'vectordb' && (
                    <VectorDBPanel settings={settings} onSave={handleSave} saving={saving} />
                )}
                {activeSubTab === 'splitter' && (
                    <TextSplitterPanel settings={settings} onSave={handleSave} saving={saving} />
                )}
                {activeSubTab === 'prompt' && (
                    <SystemPromptPanel settings={settings} onSave={handleSave} saving={saving} />
                )}
            </div>
        </div>
    );
}

function VectorDBPanel({ settings, onSave, saving }: any) {
    const [provider, setProvider] = useState(settings.VectorDB || 'lancedb');

    const providers = [
        { value: 'lancedb', label: 'LanceDB (Default)' },
        { value: 'chroma', label: 'ChromaDB' },
        { value: 'pinecone', label: 'Pinecone' },
        { value: 'milvus', label: 'Milvus' },
        { value: 'qdrant', label: 'Qdrant' },
        { value: 'weaviate', label: 'Weaviate' },
        { value: 'pgvector', label: 'PGVector' },
    ];

    return (
        <div className="space-y-4">
            <div>
                <label className="block text-sm font-medium text-[var(--ink-heading)] mb-2">
                    Vector Database Provider
                </label>
                <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                >
                    {providers.map((p) => (
                        <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                </select>
            </div>

            <button
                onClick={() => onSave({ VectorDB: provider })}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg font-medium hover:bg-emerald-600 disabled:opacity-50 transition-colors"
            >
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Save Vector DB Settings
            </button>
        </div>
    );
}

function TextSplitterPanel({ settings, onSave, saving }: any) {
    const [chunkSize, setChunkSize] = useState(settings.TextSplitterChunkSize || 1000);
    const [chunkOverlap, setChunkOverlap] = useState(settings.TextSplitterChunkOverlap || 20);

    return (
        <div className="space-y-4">
            <div>
                <label className="block text-sm font-medium text-[var(--ink-heading)] mb-2">
                    Chunk Size (characters)
                </label>
                <input
                    type="number"
                    value={chunkSize}
                    onChange={(e) => setChunkSize(Number(e.target.value))}
                    min={100}
                    max={10000}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                />
                <p className="text-xs text-[var(--ink-meta)] mt-1">
                    Recommended: 1000-2000 characters per chunk
                </p>
            </div>

            <div>
                <label className="block text-sm font-medium text-[var(--ink-heading)] mb-2">
                    Chunk Overlap (characters)
                </label>
                <input
                    type="number"
                    value={chunkOverlap}
                    onChange={(e) => setChunkOverlap(Number(e.target.value))}
                    min={0}
                    max={500}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                />
            </div>

            <button
                onClick={() => onSave({
                    text_splitter_chunk_size: chunkSize,
                    text_splitter_chunk_overlap: chunkOverlap
                })}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg font-medium hover:bg-emerald-600 disabled:opacity-50 transition-colors"
            >
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Save Text Splitter Settings
            </button>
        </div>
    );
}

function SystemPromptPanel({ settings, onSave, saving }: any) {
    const [prompt, setPrompt] = useState('');
    const [loadingPrompt, setLoadingPrompt] = useState(true);

    useEffect(() => {
        async function fetchPrompt() {
            try {
                const { defaultSystemPrompt } = await System.fetchDefaultSystemPrompt();
                setPrompt(defaultSystemPrompt || '');
            } catch (e) {
                console.error('Failed to fetch system prompt:', e);
            } finally {
                setLoadingPrompt(false);
            }
        }
        fetchPrompt();
    }, []);

    const handleSavePrompt = async () => {
        try {
            const result = await System.updateDefaultSystemPrompt(prompt);
            if (result.success) {
                showToast('System prompt updated', 'success');
            } else {
                showToast(`Error: ${result.message}`, 'error');
            }
        } catch (e) {
            showToast('Failed to save system prompt', 'error');
        }
    };

    if (loadingPrompt) {
        return (
            <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-[var(--ink-meta)]" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div>
                <label className="block text-sm font-medium text-[var(--ink-heading)] mb-2">
                    Default System Prompt
                </label>
                <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    rows={8}
                    placeholder="Enter the default system prompt for all workspaces..."
                    className="w-full px-3 py-2 rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-emerald-500/50 resize-y"
                />
                <p className="text-xs text-[var(--ink-meta)] mt-1">
                    This prompt will be used as the default for new workspaces.
                </p>
            </div>

            <button
                onClick={handleSavePrompt}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg font-medium hover:bg-emerald-600 disabled:opacity-50 transition-colors"
            >
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Save System Prompt
            </button>
        </div>
    );
}
