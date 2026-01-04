import React, { useState, useRef, useEffect } from 'react';
import { Search, Plus, ChevronDown } from 'lucide-react';
import useUser from '@/hooks/useUser';
import ActiveWorkspaces from '@/components/Sidebar/ActiveWorkspaces';
import { useNewWorkspaceModal } from '@/components/Modals/NewWorkspace';

interface LibraryViewProps {
    isCompact: boolean;
    showNewWsModal: () => void;
}

const LibraryView: React.FC<LibraryViewProps> = ({ isCompact, showNewWsModal }) => {
    const { user } = useUser();
    const [searchQuery, setSearchQuery] = useState('');
    const containerRef = useRef<HTMLDivElement>(null);
    const [showScrollAffordance, setShowScrollAffordance] = useState(false);

    // Check scroll state
    const checkScroll = () => {
        if (!containerRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
        const isScrollable = scrollHeight > clientHeight;
        const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 10;

        setShowScrollAffordance(isScrollable && !isAtBottom);
    };

    useEffect(() => {
        checkScroll();
        window.addEventListener('resize', checkScroll);
        return () => window.removeEventListener('resize', checkScroll);
    }, []);

    // Also check when content might change (e.g. workspaces load)
    // We can use a MutationObserver or just a timeout/interval if data isn't passed as prop.
    // Since ActiveWorkspaces loads data internally, we rely on user interaction or resize for now,
    // or add a MutationObserver.
    useEffect(() => {
        if (!containerRef.current) return;
        const observer = new MutationObserver(checkScroll);
        observer.observe(containerRef.current, { childList: true, subtree: true });
        return () => observer.disconnect();
    }, []);


    return (
        <div
            ref={containerRef}
            onScroll={checkScroll}
            className="flex-1 overflow-y-auto overflow-x-hidden p-2 no-scroll relative h-full"
        >
            <div className="space-y-3 pb-8">
                {!isCompact && (
                    <>
                        {/* Search */}
                        <div className="relative">
                            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
                            <input
                                type="text"
                                placeholder="Search workspaces..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-9 pr-3 py-2 bg-white border-2 border-[#CFCFCF] rounded-lg text-sm text-ink-primary placeholder-ink-border focus:outline-none focus:border-[#252525] shadow-sm"
                            />
                        </div>

                        {/* New Workspace Button */}
                        {(!user || user?.role !== 'default') && (
                            <button
                                onClick={showNewWsModal}
                                className="w-full flex items-center justify-center gap-2 rounded-lg border-2 border-[#252525] bg-transparent text-[#252525] px-4 py-2 text-sm font-semibold transition-all hover:bg-[#252525] hover:text-white"
                            >
                                <Plus size={16} />
                                <span>New Workspace</span>
                            </button>
                        )}
                    </>
                )}

                {/* Workspaces List */}
                <ActiveWorkspaces />
            </div>

            {/* Scroll Affordance Gradient */}
            <div className={`absolute bottom-0 left-0 right-0 pointer-events-none transition-opacity duration-300 flex justify-center pb-2
                ${showScrollAffordance ? 'opacity-100' : 'opacity-0'}`}>
                <div className="absolute inset-0 bg-gradient-to-t from-ink-mist via-ink-mist/80 to-transparent h-16" />
                <ChevronDown className="text-ink-primary animate-bounce relative z-10 opacity-100" size={20} />
            </div>
        </div>
    );
};

export default LibraryView;
