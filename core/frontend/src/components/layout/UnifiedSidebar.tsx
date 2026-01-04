import React, { useState, useEffect, useCallback } from 'react';
import { MessageSquare, FolderOpen, Layers, Settings, Shield, ChevronLeft, ChevronRight, Plus, Search, Globe, Building2, Users, Lock, Activity, Database, ClipboardCheck, HardDrive } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import paths from '@/utils/paths';
import useUser from '@/hooks/useUser';
import { isAdmin } from '@/utils/rbac';
import useLogo from '@/hooks/useLogo';
import { useLayerStore } from '@/store/useLayerStore';
import System from '@/models/system';
import ActiveWorkspaces from '@/components/Sidebar/ActiveWorkspaces';
import NewWorkspaceModal, { useNewWorkspaceModal } from '@/components/Modals/NewWorkspace';

import LibraryView from './LibraryView';
import ActiveContextPanel from '../ActiveContextPanel';
import BrandLogo from '../BrandLogo';

// Types
type SidebarMode = 'layers' | 'library' | 'settings';
type AccessLevel = 'READ' | 'WRITE' | 'ADMIN';

interface KnowledgeLayer {
    id: string;
    name: string;
    type: 'SYSTEM' | 'ORG' | 'TEAM' | 'USER';
    color: string;
    access: AccessLevel;
    permissions: string[];
}

// Simple cn utility
function cn(...classes: (string | boolean | undefined)[]): string {
    return classes.filter(Boolean).join(' ');
}



// Mode Tab Component
const ModeTab: React.FC<{
    mode: SidebarMode;
    icon: React.FC<{ size?: number }>;
    label: string;
    isActive: boolean;
    isCompact: boolean;
    onClick: () => void;
}> = ({ mode, icon: Icon, label, isActive, isCompact, onClick }) => {
    const isCompactStyle = isCompact
        ? "w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-200"
        : "flex-1 py-2 px-3 rounded-lg flex items-center justify-center gap-2 transition-all duration-200 text-sm font-medium";

    // Task 2: Active State (The "Ink Pill")
    const activeStyle = isActive
        ? "bg-ink-action text-white shadow-sm rounded-md font-semibold"
        : "text-ink-muted bg-transparent hover:bg-ink-panel hover:text-ink-primary font-medium";

    return (
        <button
            onClick={onClick}
            className={cn(isCompactStyle, activeStyle)}
            title={label}
        >
            <Icon size={isCompact ? 20 : 16} className={isActive ? "text-white" : "text-ink-border group-hover:text-ink-primary"} />
            {!isCompact && <span>{label}</span>}
        </button>
    );
};

// Main Component
const UnifiedSidebar: React.FC = () => {
    const { logo } = useLogo();
    const { user } = useUser();
    const location = useLocation();
    const navigate = useNavigate();

    const [mode, setMode] = useState<SidebarMode>('layers');
    const [isCompact, setIsCompact] = useState(false);

    const {
        showing: showingNewWsModal,
        showModal: showNewWsModal,
        hideModal: hideNewWsModal,
    } = useNewWorkspaceModal();

    // Auto-switch to settings mode if on settings route, and library mode if on workspace route
    useEffect(() => {
        if (location.pathname.startsWith('/settings') || location.pathname.startsWith('/admin') || location.pathname.startsWith('/engine-room')) {
            setMode('settings');
        } else if (location.pathname.startsWith('/workspace')) {
            setMode('library');
        }
    }, [location.pathname]);
    // Sidebar width based on compact state - Task 1.2: Fixed width
    // Use both w-[260px] and min-w-[260px] to prevent shrinking on different modes
    const sidebarWidth = isCompact ? 'w-16 min-w-16' : 'w-[260px] min-w-[260px]';

    return (
        <>
            <div className={cn(
                "h-full flex flex-col transition-all duration-300 ease-in-out shrink-0 z-10 relative",
                sidebarWidth,
                // Task 1.1: Background & Border (Control Panel)
                "bg-ink-mist border-r border-ink-border"
            )}>
                {/* Header: Logo + Collapse Toggle */}
                <div className={cn(
                    "flex items-center justify-between p-4 border-b border-ink-border",
                    isCompact && "flex-col gap-2"
                )}>
                    <Link to={paths.home()} className="flex items-center gap-2">
                        <div className={cn("flex items-center justify-center", isCompact ? "w-10 h-10" : "")}>
                            <BrandLogo mode={isCompact ? 'icon' : 'full'} className={isCompact ? "h-6 w-6" : "h-8 text-ink-primary"} />
                        </div>
                    </Link>
                    <button
                        onClick={() => setIsCompact(!isCompact)}
                        className="p-2 rounded-lg text-ink-muted hover:text-ink-primary hover:bg-ink-panel transition-all"
                        title={isCompact ? "Expand sidebar" : "Collapse sidebar"}
                    >
                        {isCompact ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
                    </button>
                </div>

                {/* Mode Selector */}
                <div className={cn(
                    "p-2 border-b border-ink-border",
                    isCompact ? "flex flex-col gap-1" : "flex gap-1"
                )}>
                    <ModeTab
                        mode="layers"
                        icon={Layers}
                        label="Context"
                        isActive={mode === 'layers'}
                        isCompact={isCompact}
                        onClick={() => setMode('layers')}
                    />
                    <ModeTab
                        mode="library"
                        icon={FolderOpen}
                        label="Library"
                        isActive={mode === 'library'}
                        isCompact={isCompact}
                        onClick={() => setMode('library')}
                    />
                    <ModeTab
                        mode="settings"
                        icon={Settings}
                        label="Settings"
                        isActive={mode === 'settings'}
                        isCompact={isCompact}
                        onClick={() => {
                            setMode('settings');
                            navigate('/engine-room');
                        }}
                    />
                </div>

                {/* Content Area */}
                <div className="flex-1 overflow-y-auto overflow-x-hidden p-2 no-scroll">
                    {mode === 'layers' && (
                        <ActiveContextPanel isCompact={isCompact} />
                    )}

                    {mode === 'library' && (
                        <LibraryView
                            isCompact={isCompact}
                            showNewWsModal={showNewWsModal}
                        />
                    )}

                    {mode === 'settings' && (
                        <div className="flex flex-col gap-1 p-2">
                            <p className="px-2 text-xs font-bold uppercase tracking-widest mb-2 text-ink-heading">
                                Engine Room
                            </p>
                            {[
                                { id: 'observability', label: 'Vital Signs', icon: Activity },
                                { id: 'ingestion', label: 'Ingestion Line', icon: Database },
                                { id: 'governance', label: 'Governance', icon: Shield },
                                { id: 'quality', label: 'Quality Gate', icon: ClipboardCheck },
                                { id: 'configuration', label: 'Configuration', icon: Settings },
                                { id: 'quotas', label: 'Storage Quotas', icon: HardDrive, adminOnly: true },
                                { id: 'admin', label: 'Admin Console', icon: Lock, adminOnly: true },
                            ].map((item) => {
                                if (item.adminOnly && !isAdmin()) return null;
                                return (
                                    <button
                                        key={item.id}
                                        onClick={() => {
                                            if (location.pathname !== '/engine-room') {
                                                navigate('/engine-room');
                                                setTimeout(() => {
                                                    document.getElementById(item.id)?.scrollIntoView({ behavior: 'smooth' });
                                                }, 100);
                                            } else {
                                                document.getElementById(item.id)?.scrollIntoView({ behavior: 'smooth' });
                                            }
                                        }}
                                        className={cn(
                                            "w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 transition-all duration-200 text-sm",
                                            "text-ink-muted hover:bg-ink-panel hover:text-ink-primary",
                                            isCompact && "justify-center px-0"
                                        )}
                                        title={item.label}
                                    >
                                        <item.icon size={16} />
                                        {!isCompact && <span>{item.label}</span>}
                                    </button>
                                );
                            })}
                        </div>
                    )}

                </div>

                {/* Footer: Status Only */}
                <div className={cn(
                    "p-3 border-t border-ink-border/20 space-y-2",
                    isCompact && "flex flex-col items-center"
                )}>
                    {/* System Status */}
                    <div className={cn(
                        "flex items-center gap-2",
                        isCompact ? "justify-center" : "px-2"
                    )}>
                        <div className="w-2 h-2 rounded-full bg-ink-primary shadow-[0_0_2px_#252525]" />
                        {!isCompact && (
                            <span className="text-[10px] text-ink-muted uppercase tracking-wider">System Online</span>
                        )}
                    </div>
                </div>
            </div>

            {showingNewWsModal && <NewWorkspaceModal hideModal={hideNewWsModal} />}
        </>
    );
};

export default UnifiedSidebar;
