import React, { useState, useEffect } from 'react';
import { Palette, ImageIcon, MessageCircle, Save, Loader2 } from 'lucide-react';
import System from '@/models/system';
import showToast from '@/utils/toast';

type SubTab = 'interface' | 'branding' | 'chat';

export default function CustomizationSection() {
    const [activeSubTab, setActiveSubTab] = useState<SubTab>('interface');
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
        { id: 'interface', label: 'Interface', icon: <Palette size={16} /> },
        { id: 'branding', label: 'Branding', icon: <ImageIcon size={16} /> },
        { id: 'chat', label: 'Chat Defaults', icon: <MessageCircle size={16} /> },
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
                {activeSubTab === 'interface' && (
                    <InterfacePanel settings={settings} onSave={handleSave} saving={saving} />
                )}
                {activeSubTab === 'branding' && (
                    <BrandingPanel settings={settings} onSave={handleSave} saving={saving} />
                )}
                {activeSubTab === 'chat' && (
                    <ChatDefaultsPanel settings={settings} onSave={handleSave} saving={saving} />
                )}
            </div>
        </div>
    );
}

function InterfacePanel({ settings, onSave, saving }: any) {
    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Interface Settings</h3>

            <div className="p-4 bg-white rounded-lg border border-[var(--ink-border)]">
                <p className="text-sm text-[var(--ink-meta)]">
                    Interface customization options will be available here. The PandoraLM "Ink Wash" theme is currently active.
                </p>
            </div>
        </div>
    );
}

function BrandingPanel({ settings, onSave, saving }: any) {
    const [appName, setAppName] = useState('');

    useEffect(() => {
        async function fetchAppName() {
            const { appName: name } = await System.fetchCustomAppName();
            setAppName(name || '');
        }
        fetchAppName();
    }, []);

    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Branding</h3>

            <div>
                <label className="block text-sm font-medium text-[var(--ink-heading)] mb-2">
                    Custom App Name
                </label>
                <input
                    type="text"
                    value={appName}
                    onChange={(e) => setAppName(e.target.value)}
                    placeholder="PandoraLM"
                    className="w-full px-3 py-2 rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                />
                <p className="text-xs text-[var(--ink-meta)] mt-1">
                    Leave blank to use default "PandoraLM" branding.
                </p>
            </div>

            <button
                onClick={() => onSave({ custom_app_name: appName })}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg font-medium hover:bg-emerald-600 disabled:opacity-50 transition-colors"
            >
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Save Branding
            </button>
        </div>
    );
}

function ChatDefaultsPanel({ settings, onSave, saving }: any) {
    const [welcomeMessages, setWelcomeMessages] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchMessages() {
            try {
                const messages = await System.getWelcomeMessages();
                setWelcomeMessages(messages || []);
            } catch (e) {
                console.error('Failed to fetch welcome messages:', e);
            } finally {
                setLoading(false);
            }
        }
        fetchMessages();
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
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Chat Defaults</h3>

            <div className="p-4 bg-white rounded-lg border border-[var(--ink-border)]">
                <p className="text-sm font-medium text-[var(--ink-body)] mb-2">Welcome Messages</p>
                <p className="text-xs text-[var(--ink-meta)]">
                    Configure the messages shown when a user starts a new chat.
                    {welcomeMessages.length > 0 ? ` Currently ${welcomeMessages.length} message(s) configured.` : ' No custom messages configured.'}
                </p>
            </div>
        </div>
    );
}
