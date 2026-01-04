import React, { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import UnifiedSidebar from '../components/layout/UnifiedSidebar';
import StoreHydrator from '../components/utils/StoreHydrator';
import { IntelligenceSidePanel } from '../components/IntelligencePanel';
import { useGlassBoxSafe } from '../contexts/GlassBoxContext';
import { IntelligenceMode } from '../components/IntelligencePanel';

interface TriPaneLayoutProps {
    children: React.ReactNode;
}

const TriPaneLayout: React.FC<TriPaneLayoutProps> = ({ children }) => {
    const location = useLocation();
    const glassBox = useGlassBoxSafe();

    // Routes where we should hide the OS chrome (Sidebar, Panels)
    const publicRoutes = ['/login', '/onboarding', '/accept-invite', '/sso'];
    const isPublicRoute = publicRoutes.some(route => location.pathname.startsWith(route));

    // Determine Intelligence Panel State
    const { mode, data } = useMemo(() => {
        if (!glassBox) return { mode: 'CLOSED' as IntelligenceMode, data: null };
        if (glassBox.pendingMeetingRef) return { mode: 'MEETING' as IntelligenceMode, data: glassBox.pendingMeetingRef };
        if (glassBox.pendingGraphViz) return { mode: 'GRAPH' as IntelligenceMode, data: glassBox.pendingGraphViz };
        if (glassBox.pendingCodeBlock) return { mode: 'CODE' as IntelligenceMode, data: glassBox.pendingCodeBlock };
        return { mode: 'CLOSED' as IntelligenceMode, data: null };
    }, [glassBox?.pendingMeetingRef, glassBox?.pendingGraphViz, glassBox?.pendingCodeBlock]);

    const handleClosePanel = () => {
        if (!glassBox) return;
        if (glassBox.pendingMeetingRef) glassBox.dismissPanelTrigger('meeting_ref');
        if (glassBox.pendingGraphViz) glassBox.dismissPanelTrigger('graph_viz');
        if (glassBox.pendingCodeBlock) glassBox.dismissPanelTrigger('code_block');
    };

    return (
        <StoreHydrator>
            <div className="h-screen w-screen overflow-hidden flex">
                {/* Unified Sidebar - Merged Dock + KnowledgeRail + Library */}
                {!isPublicRoute && <UnifiedSidebar />}

                {/* Main Canvas (The Wall) */}
                <div className="flex-1 h-full relative min-w-0 flex bg-[var(--ink-wall)]">
                    <div
                        className="flex-1 h-full relative min-w-0 overflow-y-auto overflow-x-hidden"
                    >
                        {children}
                    </div>

                    {/* Intelligence Side Panel (Collapsible) */}
                    {!isPublicRoute && mode !== 'CLOSED' && (
                        <div className="absolute right-0 top-0 h-full z-20 shadow-2xl animate-fade-in-left">
                            <IntelligenceSidePanel
                                mode={mode}
                                data={data}
                                onClose={handleClosePanel}
                                layerId="system_public" // TODO: Fetch from context if available
                            />
                        </div>
                    )}
                </div>
            </div>
        </StoreHydrator>
    );
};

export default TriPaneLayout;

