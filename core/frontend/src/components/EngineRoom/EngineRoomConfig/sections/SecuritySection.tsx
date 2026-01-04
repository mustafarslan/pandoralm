import React, { useState, useEffect } from 'react';
import { Lock, Eye, Key, FileText, Save, Loader2, Copy, Trash2, Plus } from 'lucide-react';
import System from '@/models/system';
import showToast from '@/utils/toast';

type SubTab = 'auth' | 'privacy' | 'apikeys' | 'logs';

export default function SecuritySection() {
    const [activeSubTab, setActiveSubTab] = useState<SubTab>('auth');

    const subTabs = [
        { id: 'auth', label: 'Authentication', icon: <Lock size={16} /> },
        { id: 'privacy', label: 'Privacy', icon: <Eye size={16} /> },
        { id: 'apikeys', label: 'API Keys', icon: <Key size={16} /> },
        { id: 'logs', label: 'Event Logs', icon: <FileText size={16} /> },
    ];

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
                {activeSubTab === 'auth' && <AuthPanel />}
                {activeSubTab === 'privacy' && <PrivacyPanel />}
                {activeSubTab === 'apikeys' && <APIKeysPanel />}
                {activeSubTab === 'logs' && <EventLogsPanel />}
            </div>
        </div>
    );
}

function AuthPanel() {
    const [settings, setSettings] = useState<any>({});
    const [loading, setLoading] = useState(true);

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

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-[var(--ink-meta)]" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Authentication Settings</h3>

            <div className="p-4 bg-white rounded-lg border border-[var(--ink-border)]">
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-sm font-medium text-[var(--ink-body)]">Multi-User Mode</p>
                        <p className="text-xs text-[var(--ink-meta)]">
                            {settings.RequiresAuth ? 'Enabled - Users must log in' : 'Disabled - Single user mode'}
                        </p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${settings.RequiresAuth ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-700'
                        }`}>
                        {settings.RequiresAuth ? 'Enabled' : 'Disabled'}
                    </span>
                </div>
            </div>

            <p className="text-xs text-[var(--ink-meta)]">
                To enable multi-user mode, use the onboarding flow or update environment variables.
            </p>
        </div>
    );
}

function PrivacyPanel() {
    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Privacy Settings</h3>

            <div className="p-4 bg-white rounded-lg border border-[var(--ink-border)]">
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-sm font-medium text-[var(--ink-body)]">Telemetry</p>
                        <p className="text-xs text-[var(--ink-meta)]">
                            PandoraLM does not collect any telemetry data.
                        </p>
                    </div>
                    <span className="px-3 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
                        Disabled
                    </span>
                </div>
            </div>
        </div>
    );
}

function APIKeysPanel() {
    const [apiKeys, setApiKeys] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);

    useEffect(() => {
        fetchApiKeys();
    }, []);

    const fetchApiKeys = async () => {
        try {
            const { apiKeys: keys } = await System.getApiKeys();
            setApiKeys(keys || []);
        } catch (e) {
            console.error('Failed to fetch API keys:', e);
        } finally {
            setLoading(false);
        }
    };

    const handleGenerate = async () => {
        setGenerating(true);
        try {
            const { apiKey, error } = await System.generateApiKey();
            if (error) {
                showToast(`Error: ${error}`, 'error');
            } else {
                showToast('API key generated!', 'success');
                fetchApiKeys();
            }
        } catch (e) {
            showToast('Failed to generate API key', 'error');
        } finally {
            setGenerating(false);
        }
    };

    const handleDelete = async (id: string) => {
        try {
            const success = await System.deleteApiKey(id);
            if (success) {
                showToast('API key deleted', 'success');
                setApiKeys(apiKeys.filter(k => k.id !== id));
            }
        } catch (e) {
            showToast('Failed to delete API key', 'error');
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        showToast('Copied to clipboard', 'success');
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-[var(--ink-meta)]" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h3 className="text-sm font-semibold text-[var(--ink-heading)]">API Keys</h3>
                <button
                    onClick={handleGenerate}
                    disabled={generating}
                    className="flex items-center gap-1 px-3 py-1.5 bg-emerald-500 text-white rounded-lg text-sm font-medium hover:bg-emerald-600 disabled:opacity-50 transition-colors"
                >
                    {generating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                    Generate Key
                </button>
            </div>

            <div className="space-y-2">
                {apiKeys.map((key) => (
                    <div key={key.id} className="flex items-center justify-between p-3 bg-white rounded-lg border border-[var(--ink-border)]">
                        <div className="flex-1">
                            <code className="text-sm font-mono text-[var(--ink-body)]">
                                {key.secret ? `${key.secret.slice(0, 20)}...` : 'Hidden'}
                            </code>
                            <p className="text-xs text-[var(--ink-meta)] mt-1">
                                Created: {new Date(key.createdAt).toLocaleDateString()}
                            </p>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => copyToClipboard(key.secret)}
                                className="p-1.5 text-[var(--ink-meta)] hover:text-[var(--ink-body)]"
                            >
                                <Copy size={14} />
                            </button>
                            <button
                                onClick={() => handleDelete(key.id)}
                                className="p-1.5 text-red-500 hover:text-red-700"
                            >
                                <Trash2 size={14} />
                            </button>
                        </div>
                    </div>
                ))}
                {apiKeys.length === 0 && (
                    <p className="py-8 text-center text-[var(--ink-meta)]">
                        No API keys generated yet.
                    </p>
                )}
            </div>
        </div>
    );
}

function EventLogsPanel() {
    const [logs, setLogs] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchLogs() {
            try {
                const { logs: data } = await System.eventLogs();
                setLogs(data || []);
            } catch (e) {
                console.error('Failed to fetch logs:', e);
            } finally {
                setLoading(false);
            }
        }
        fetchLogs();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-[var(--ink-meta)]" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Event Logs</h3>

            <div className="max-h-96 overflow-y-auto space-y-2">
                {logs.map((log, i) => (
                    <div key={i} className="p-3 bg-white rounded-lg border border-[var(--ink-border)]">
                        <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-[var(--ink-body)]">{log.event}</span>
                            <span className="text-xs text-[var(--ink-meta)]">
                                {new Date(log.createdAt).toLocaleString()}
                            </span>
                        </div>
                        {log.metadata && (
                            <p className="text-xs text-[var(--ink-meta)] mt-1 font-mono">
                                {JSON.stringify(log.metadata)}
                            </p>
                        )}
                    </div>
                ))}
                {logs.length === 0 && (
                    <p className="py-8 text-center text-[var(--ink-meta)]">
                        No event logs recorded yet.
                    </p>
                )}
            </div>
        </div>
    );
}
