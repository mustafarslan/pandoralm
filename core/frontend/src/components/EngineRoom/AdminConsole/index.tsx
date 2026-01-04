import React, { useState } from 'react';
import { Database, Network, ChevronDown, ChevronUp, Activity } from 'lucide-react';
import VisualInspector from './VectorOps/VisualInspector';
import ChunkEditor from './VectorOps/ChunkEditor';
import DocumentManager from './VectorOps/DocumentManager';
import EntityManager from './GraphOps/EntityManager';
import RelationshipGraph from './GraphOps/RelationshipGraph';
import CommunitySummaries from './GraphOps/CommunitySummaries';

// Mock components until implemented
// const VisualInspector = () => <div className="p-4">Visual Inspector Component</div>;
// const ChunkEditor = () => <div className="p-4">Chunk Editor Component</div>;
// const DocumentManager = () => <div className="p-4">Document Manager Component</div>;
// const EntityManager = () => <div className="p-4">Entity Manager Component</div>;
// const RelationshipGraph = () => <div className="p-4">Relationship Graph Component</div>;
// const CommunitySummaries = () => <div className="p-4">Community Summaries Component</div>;


import SystemHealth from './Overview/SystemHealth';
import QuickActions from './Overview/QuickActions';

type TabId = 'overview' | 'vector' | 'graph';
type SubTab = 'inspect' | 'edit' | 'context' | 'entities' | 'relationships' | 'communities';

interface Tab {
    id: TabId;
    label: string;
    icon: React.ReactNode;
}

const TABS: Tab[] = [
    { id: 'overview', label: 'Overview', icon: <Activity size={18} /> },
    { id: 'vector', label: 'Vector Operations', icon: <Database size={18} /> },
    { id: 'graph', label: 'Graph Operations', icon: <Network size={18} /> },
];

export const AdminConsoleConfig = () => {
    const [activeTab, setActiveTab] = useState<TabId>('overview');
    const [activeSubTab, setActiveSubTab] = useState<SubTab>('inspect');
    const [isCollapsed, setIsCollapsed] = useState(false);

    // Reset subtab when main tab changes
    const handleTabChange = (tabId: TabId) => {
        setActiveTab(tabId);
        if (tabId === 'vector') setActiveSubTab('inspect');
        if (tabId === 'graph') setActiveSubTab('entities');
    };

    return (
        <div className="pb-6">
            {/* Section Header */}


            {!isCollapsed && (
                <div className="bg-[var(--ink-card)] border border-[var(--ink-border)] rounded-xl overflow-hidden shadow-sm">
                    {/* Main Tab Navigation */}
                    <div className="flex border-b border-[var(--ink-border)]">
                        {TABS.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => handleTabChange(tab.id)}
                                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${activeTab === tab.id
                                    ? 'border-black text-[var(--ink-heading)] bg-[var(--ink-page)]'
                                    : 'border-transparent text-[var(--ink-meta)] hover:text-[var(--ink-heading)] hover:bg-[var(--ink-page)]/50'
                                    }`}
                            >
                                {tab.icon}
                                <span>{tab.label}</span>
                            </button>
                        ))}
                    </div>

                    {/* Sub-tab Navigation & Content */}
                    <div className="p-6">
                        {activeTab === 'overview' ? (
                            <div>
                                <SystemHealth />
                                <QuickActions />
                            </div>
                        ) : activeTab === 'vector' ? (
                            <div className="space-y-6">
                                <div className="flex gap-2 border-b border-[var(--ink-border)] pb-4">
                                    <button
                                        onClick={() => setActiveSubTab('inspect')}
                                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeSubTab === 'inspect' ? 'bg-ink-action text-white' : 'text-ink-muted hover:bg-ink-panel hover:text-ink-primary'}`}
                                    >
                                        Visual Inspector
                                    </button>
                                    <button
                                        onClick={() => setActiveSubTab('edit')}
                                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeSubTab === 'edit' ? 'bg-ink-action text-white' : 'text-ink-muted hover:bg-ink-panel hover:text-ink-primary'}`}
                                    >
                                        Surgical Editing
                                    </button>
                                    <button
                                        onClick={() => setActiveSubTab('context')}
                                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeSubTab === 'context' ? 'bg-ink-action text-white' : 'text-ink-muted hover:bg-ink-panel hover:text-ink-primary'}`}
                                    >
                                        Context Management
                                    </button>
                                </div>

                                <div className="bg-[var(--ink-page)] rounded-lg border border-[var(--ink-border)] min-h-[400px]">
                                    {activeSubTab === 'inspect' && <VisualInspector />}
                                    {activeSubTab === 'edit' && <ChunkEditor />}
                                    {activeSubTab === 'context' && <DocumentManager />}
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-6">
                                <div className="flex gap-2 border-b border-[var(--ink-border)] pb-4">
                                    <button
                                        onClick={() => setActiveSubTab('entities')}
                                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeSubTab === 'entities' ? 'bg-ink-action text-white' : 'text-ink-muted hover:bg-ink-panel hover:text-ink-primary'}`}
                                    >
                                        Entity Manager
                                    </button>
                                    <button
                                        onClick={() => setActiveSubTab('relationships')}
                                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeSubTab === 'relationships' ? 'bg-ink-action text-white' : 'text-ink-muted hover:bg-ink-panel hover:text-ink-primary'}`}
                                    >
                                        Relationship Inspector
                                    </button>
                                    <button
                                        onClick={() => setActiveSubTab('communities')}
                                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeSubTab === 'communities' ? 'bg-ink-action text-white' : 'text-ink-muted hover:bg-ink-panel hover:text-ink-primary'}`}
                                    >
                                        Community Summaries
                                    </button>
                                </div>

                                <div className="bg-[var(--ink-page)] rounded-lg border border-[var(--ink-border)] min-h-[400px]">
                                    {activeSubTab === 'entities' && <EntityManager />}
                                    {activeSubTab === 'relationships' && <RelationshipGraph />}
                                    {activeSubTab === 'communities' && <CommunitySummaries />}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};


export default AdminConsoleConfig;
