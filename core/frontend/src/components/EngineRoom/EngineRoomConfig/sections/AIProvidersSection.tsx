import React, { useState, useEffect } from 'react';
import { Cpu, Bot, Mic, Volume2, Save, Loader2, RefreshCw } from 'lucide-react';
import System from '@/models/system';
import showToast from '@/utils/toast';
import { cortexGet } from '@/utils/cortexApi';

type SubTab = 'llm' | 'embedding' | 'transcription' | 'tts';

export default function AIProvidersSection() {
    const [activeSubTab, setActiveSubTab] = useState<SubTab>('llm');
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
        { id: 'llm', label: 'LLM Provider', icon: <Bot size={16} /> },
        { id: 'embedding', label: 'Embedding', icon: <Cpu size={16} /> },
        { id: 'transcription', label: 'Transcription', icon: <Mic size={16} /> },
        { id: 'tts', label: 'Text-to-Speech', icon: <Volume2 size={16} /> },
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
            {/* Sub-tabs */}
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

            {/* Content */}
            <div className="bg-[var(--ink-page)] rounded-lg border border-[var(--ink-border)] p-4">
                {activeSubTab === 'llm' && (
                    <LLMProviderPanel settings={settings} onSave={handleSave} saving={saving} />
                )}
                {activeSubTab === 'embedding' && (
                    <EmbeddingPanel settings={settings} onSave={handleSave} saving={saving} />
                )}
                {activeSubTab === 'transcription' && (
                    <TranscriptionPanel settings={settings} onSave={handleSave} saving={saving} />
                )}
                {activeSubTab === 'tts' && (
                    <TTSPanel settings={settings} onSave={handleSave} saving={saving} />
                )}
            </div>
        </div>
    );
}

// LLM Provider Panel
function LLMProviderPanel({ settings, onSave, saving }: any) {
    const [provider, setProvider] = useState(settings.LLMProvider || 'ollama');
    const [baseUrl, setBaseUrl] = useState(settings.OllamaLLMBasePath || 'http://localhost:11434');
    const [model, setModel] = useState(settings.OllamaLLMModelPref || '');

    // Dynamic Model List State
    const [availableModels, setAvailableModels] = useState<string[]>([]);
    const [fetchingModels, setFetchingModels] = useState(false);

    const fetchModels = async () => {
        if (provider !== 'ollama' && provider !== 'openai') return; // Only support list for some providers for now
        setFetchingModels(true);
        try {
            const models = await cortexGet<string[]>(`/api/v1/system/models/available?provider=${provider}`);
            setAvailableModels(models || []);
            showToast(`Fetched ${models?.length || 0} models`, 'success');
        } catch (e) {
            console.error(e);
            showToast('Failed to fetch models', 'error');
        } finally {
            setFetchingModels(false);
        }
    };

    // Auto-fetch on provider change or load
    useEffect(() => {
        if (provider === 'ollama') fetchModels();
    }, [provider]);

    const providers = [
        { value: 'ollama', label: 'Ollama' },
        { value: 'openai', label: 'OpenAI' },
        { value: 'anthropic', label: 'Anthropic' },
        { value: 'azure', label: 'Azure OpenAI' },
        { value: 'gemini', label: 'Google Gemini' },
    ];

    return (
        <div className="space-y-4">
            <div>
                <label className="block text-sm font-medium text-[var(--ink-heading)] mb-2">
                    LLM Provider
                </label>
                <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-black/5"
                >
                    {providers.map((p) => (
                        <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                </select>
            </div>

            {provider === 'ollama' && (
                <>
                    <div>
                        <label className="block text-sm font-medium text-[var(--ink-heading)] mb-2">
                            Ollama Base URL
                        </label>
                        <input
                            type="text"
                            value={baseUrl}
                            onChange={(e) => setBaseUrl(e.target.value)}
                            placeholder="http://localhost:11434"
                            className="w-full px-3 py-2 rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-black/5"
                        />
                    </div>
                    <div>
                        <div className="flex justify-between items-center mb-2">
                            <label className="block text-sm font-medium text-[var(--ink-heading)]">
                                Model Selection
                            </label>
                            <button
                                onClick={fetchModels}
                                disabled={fetchingModels}
                                className="text-xs text-[var(--ink-meta)] flex items-center gap-1 hover:text-[var(--ink-heading)]"
                            >
                                <RefreshCw size={10} className={fetchingModels ? 'animate-spin' : ''} />
                                Refresh List
                            </button>
                        </div>

                        {availableModels.length > 0 ? (
                            <select
                                value={model}
                                onChange={(e) => setModel(e.target.value)}
                                className="w-full px-3 py-2 rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-black/5 pr-10"
                            >
                                <option value="" disabled>Select a model...</option>
                                {availableModels.map(m => (
                                    <option key={m} value={m}>{m}</option>
                                ))}
                            </select>
                        ) : (
                            <select
                                disabled
                                className="w-full px-3 py-2 rounded-lg border border-[var(--ink-border)] bg-neutral-100 text-[var(--ink-muted)] cursor-not-allowed"
                            >
                                <option>No models available (Refresh List)</option>
                            </select>
                        )}
                    </div>
                </>
            )}

            <button
                onClick={() => onSave({
                    LLMProvider: provider,
                    OllamaLLMBasePath: baseUrl,
                    OllamaLLMModelPref: model
                })}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-neutral-900 text-white rounded-lg font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
            >
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Save LLM Settings
            </button>
        </div>
    );
}

// Embedding Panel
function EmbeddingPanel({ settings, onSave, saving }: any) {
    const [provider, setProvider] = useState(settings.EmbeddingEngine || 'native');

    const providers = [
        { value: 'native', label: 'Native Embedder (Built-in)' },
        { value: 'openai', label: 'OpenAI' },
        { value: 'ollama', label: 'Ollama' },
    ];

    return (
        <div className="space-y-4">
            <div>
                <label className="block text-sm font-medium text-[var(--ink-heading)] mb-2">
                    Embedding Provider
                </label>
                <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-black/5"
                >
                    {providers.map((p) => (
                        <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                </select>
            </div>

            <button
                onClick={() => onSave({ EmbeddingEngine: provider })}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-neutral-900 text-white rounded-lg font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
            >
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Save Embedding Settings
            </button>
        </div>
    );
}

// Transcription Panel
function TranscriptionPanel({ settings, onSave, saving }: any) {
    const [provider, setProvider] = useState(settings.TranscriptionProvider || 'native');

    return (
        <div className="space-y-4">
            <div>
                <label className="block text-sm font-medium text-[var(--ink-heading)] mb-2">
                    Transcription Provider
                </label>
                <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-black/5"
                >
                    <option value="native">Native (Built-in)</option>
                    <option value="openai">OpenAI Whisper</option>
                </select>
            </div>

            <button
                onClick={() => onSave({ TranscriptionProvider: provider })}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-neutral-900 text-white rounded-lg font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
            >
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Save Transcription Settings
            </button>
        </div>
    );
}

// TTS Panel
function TTSPanel({ settings, onSave, saving }: any) {
    const [provider, setProvider] = useState(settings.TTSProvider || 'native');

    return (
        <div className="space-y-4">
            <div>
                <label className="block text-sm font-medium text-[var(--ink-heading)] mb-2">
                    Text-to-Speech Provider
                </label>
                <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-black/5"
                >
                    <option value="native">Browser Native</option>
                    <option value="openai">OpenAI TTS</option>
                    <option value="elevenlabs">ElevenLabs</option>
                    <option value="piper">Piper TTS</option>
                </select>
            </div>

            <button
                onClick={() => onSave({ TTSProvider: provider })}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-neutral-900 text-white rounded-lg font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
            >
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Save TTS Settings
            </button>
        </div>
    );
}

function ChevronDown({ size, className }: { size: number, className: string }) {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
        >
            <path d="m6 9 6 6 6-6" />
        </svg>
    );
}
