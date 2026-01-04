import React, { useState } from 'react';
import { Bot, Variable, Code, Puzzle, Smartphone, FlaskConical } from 'lucide-react';

type SubTab = 'agents' | 'variables' | 'widgets' | 'extensions' | 'mobile' | 'beta';

export default function AdvancedSection() {
    const [activeSubTab, setActiveSubTab] = useState<SubTab>('agents');

    const subTabs = [
        { id: 'agents', label: 'Agent Skills', icon: <Bot size={16} /> },
        { id: 'variables', label: 'Prompt Variables', icon: <Variable size={16} /> },
        { id: 'widgets', label: 'Embed Widgets', icon: <Code size={16} /> },
        { id: 'extensions', label: 'Browser Ext.', icon: <Puzzle size={16} /> },
        { id: 'mobile', label: 'Mobile', icon: <Smartphone size={16} /> },
        { id: 'beta', label: 'Beta Features', icon: <FlaskConical size={16} /> },
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
                {activeSubTab === 'agents' && <AgentSkillsPanel />}
                {activeSubTab === 'variables' && <PromptVariablesPanel />}
                {activeSubTab === 'widgets' && <EmbedWidgetsPanel />}
                {activeSubTab === 'extensions' && <BrowserExtensionPanel />}
                {activeSubTab === 'mobile' && <MobilePanel />}
                {activeSubTab === 'beta' && <BetaFeaturesPanel />}
            </div>
        </div>
    );
}

function AgentSkillsPanel() {
    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Agent Skills</h3>
            <p className="text-sm text-[var(--ink-meta)]">
                Configure available skills for workspace agents. Skills can include web browsing, code execution, SQL queries, and more.
            </p>
            <div className="py-8 text-center text-[var(--ink-meta)] border border-dashed border-[var(--ink-border)] rounded-lg">
                Agent skills configuration coming soon...
            </div>
        </div>
    );
}

function PromptVariablesPanel() {
    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">System Prompt Variables</h3>
            <p className="text-sm text-[var(--ink-meta)]">
                Define dynamic variables that can be used in system prompts. Variables are replaced at runtime.
            </p>
            <div className="py-8 text-center text-[var(--ink-meta)] border border-dashed border-[var(--ink-border)] rounded-lg">
                Prompt variables configuration coming soon...
            </div>
        </div>
    );
}

function EmbedWidgetsPanel() {
    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Embed Chat Widgets</h3>
            <p className="text-sm text-[var(--ink-meta)]">
                Create embeddable chat widgets for external websites. Configure appearance and behavior.
            </p>
            <div className="py-8 text-center text-[var(--ink-meta)] border border-dashed border-[var(--ink-border)] rounded-lg">
                Embed widget configuration coming soon...
            </div>
        </div>
    );
}

function BrowserExtensionPanel() {
    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Browser Extension</h3>
            <p className="text-sm text-[var(--ink-meta)]">
                Connect PandoraLM to your browser for quick access and document ingestion.
            </p>
            <div className="py-8 text-center text-[var(--ink-meta)] border border-dashed border-[var(--ink-border)] rounded-lg">
                Browser extension setup coming soon...
            </div>
        </div>
    );
}

function MobilePanel() {
    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Mobile Connections</h3>
            <p className="text-sm text-[var(--ink-meta)]">
                Connect mobile apps to your PandoraLM instance for on-the-go access.
            </p>
            <div className="py-8 text-center text-[var(--ink-meta)] border border-dashed border-[var(--ink-border)] rounded-lg">
                Mobile connection setup coming soon...
            </div>
        </div>
    );
}

function BetaFeaturesPanel() {
    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Beta Features</h3>
            <p className="text-sm text-[var(--ink-meta)]">
                Enable experimental features. These may be unstable or change without notice.
            </p>

            <div className="p-4 bg-white rounded-lg border border-[var(--ink-border)]">
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-sm font-medium text-[var(--ink-body)]">Live Document Sync</p>
                        <p className="text-xs text-[var(--ink-meta)]">
                            Automatically re-index documents when source files change.
                        </p>
                    </div>
                    <span className="px-3 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                        Beta
                    </span>
                </div>
            </div>
        </div>
    );
}
