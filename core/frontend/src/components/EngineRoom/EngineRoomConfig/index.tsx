import React, { useState } from 'react';
import {
    Cpu,
    Database,
    Users,
    Shield,
    Palette,
    Wrench,
    ChevronDown,
    ChevronUp
} from 'lucide-react';

// Import section components
import AIProvidersSection from './sections/AIProvidersSection';
import StorageSection from './sections/StorageSection';
import UserManagementSection from './sections/UserManagementSection';
import SecuritySection from './sections/SecuritySection';
import CustomizationSection from './sections/CustomizationSection';
import AdvancedSection from './sections/AdvancedSection';

type TabId = 'ai' | 'storage' | 'users' | 'security' | 'customization' | 'advanced';

interface Tab {
    id: TabId;
    label: string;
    icon: React.ReactNode;
    description: string;
}

const TABS: Tab[] = [
    { id: 'ai', label: 'AI Providers', icon: <Cpu size={18} />, description: 'LLM, Embedding, Transcription, TTS' },
    { id: 'storage', label: 'Storage', icon: <Database size={18} />, description: 'Vector DB, Text Splitter, System Prompt' },
    { id: 'users', label: 'Users', icon: <Users size={18} />, description: 'User Management, Invites, Workspaces' },
    { id: 'security', label: 'Security', icon: <Shield size={18} />, description: 'Auth, Privacy, API Keys, Logs' },
    { id: 'customization', label: 'Customization', icon: <Palette size={18} />, description: 'Interface, Branding, Chat' },
    { id: 'advanced', label: 'Advanced', icon: <Wrench size={18} />, description: 'Agents, Variables, Widgets' },
];

const SECTION_COMPONENTS: Record<TabId, React.ComponentType> = {
    ai: AIProvidersSection,
    storage: StorageSection,
    users: UserManagementSection,
    security: SecuritySection,
    customization: CustomizationSection,
    advanced: AdvancedSection,
};

export const EngineRoomConfig = () => {
    const [activeTab, setActiveTab] = useState<TabId>('ai');
    const [isCollapsed, setIsCollapsed] = useState(false);

    const ActiveSection = SECTION_COMPONENTS[activeTab];

    return (
        <div className="pb-6">
            {/* Section Header */}


            {!isCollapsed && (
                <div className="bg-[var(--ink-card)] border border-[var(--ink-border)] rounded-xl overflow-hidden shadow-sm">
                    {/* Tab Navigation */}
                    <div className="flex border-b border-[var(--ink-border)] overflow-x-auto">
                        {TABS.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`flex items-center gap-2 px-4 py-3 text-sm font-bold whitespace-nowrap transition-colors border-b-2 -mb-px ${activeTab === tab.id
                                    ? 'border-black text-black bg-neutral-100'
                                    : 'border-transparent text-neutral-500 hover:text-black hover:bg-neutral-50'
                                    }`}
                            >
                                {tab.icon}
                                <span className="hidden sm:inline">{tab.label}</span>
                            </button>
                        ))}
                    </div>

                    {/* Tab Description */}
                    <div className="px-6 py-3 bg-[var(--ink-page)] border-b border-[var(--ink-border)]">
                        <p className="text-sm text-[var(--ink-meta)]">
                            {TABS.find(t => t.id === activeTab)?.description}
                        </p>
                    </div>

                    {/* Tab Content */}
                    <div className="p-6">
                        <ActiveSection />
                    </div>
                </div>
            )}
        </div>
    );
};

export default EngineRoomConfig;
