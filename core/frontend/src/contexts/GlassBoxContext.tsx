import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import type { ThoughtStep, CognitiveTier } from '../components/chat/ThoughtAccordion';
import type { DataPayload, MeetingRefPayload, GraphVizPayload, CodeBlockPayload } from '../utils/streamParser';

/**
 * Glass Box State - Manages the cognitive process visualization
 */
interface GlassBoxState {
    // Thought tracking
    thoughts: ThoughtStep[];
    currentTier: CognitiveTier;
    isThinking: boolean;

    // Panel triggers (for Side Panel)
    pendingMeetingRef: MeetingRefPayload | null;
    pendingGraphViz: GraphVizPayload | null;
    pendingCodeBlock: CodeBlockPayload | null;

    // Actions
    addThought: (thought: ThoughtStep) => void;
    setTier: (tier: CognitiveTier) => void;
    setThinking: (thinking: boolean) => void;
    clearThoughts: () => void;
    setMeetingRef: (ref: MeetingRefPayload | null) => void;
    setGraphViz: (viz: GraphVizPayload | null) => void;
    setCodeBlock: (block: CodeBlockPayload | null) => void;
    dismissPanelTrigger: (type: 'meeting_ref' | 'graph_viz' | 'code_block') => void;
    processDataPayload: (payload: DataPayload) => void;
}

const GlassBoxContext = createContext<GlassBoxState | null>(null);

/**
 * Hook to access Glass Box state
 */
export function useGlassBox(): GlassBoxState {
    const context = useContext(GlassBoxContext);
    if (!context) {
        throw new Error('useGlassBox must be used within a GlassBoxProvider');
    }
    return context;
}

/**
 * Safe version that returns null if not in provider
 */
export function useGlassBoxSafe(): GlassBoxState | null {
    return useContext(GlassBoxContext);
}

interface GlassBoxProviderProps {
    children: React.ReactNode;
}

/**
 * GlassBoxProvider - Provides cognitive process visualization state
 * 
 * This context allows the chat components to coordinate:
 * - Thought step visualization (ThoughtAccordion)
 * - Cognitive tier tracking (System 1 vs System 2)
 * - Side panel triggers (Meeting, Graph, Code)
 */
export function GlassBoxProvider({ children }: GlassBoxProviderProps) {
    const [thoughts, setThoughts] = useState<ThoughtStep[]>([]);
    const [currentTier, setCurrentTier] = useState<CognitiveTier>('SYSTEM_1');
    const [isThinking, setIsThinking] = useState(false);
    const [pendingMeetingRef, setPendingMeetingRef] = useState<MeetingRefPayload | null>(null);
    const [pendingGraphViz, setPendingGraphViz] = useState<GraphVizPayload | null>(null);
    const [pendingCodeBlock, setPendingCodeBlock] = useState<CodeBlockPayload | null>(null);

    const addThought = useCallback((thought: ThoughtStep) => {
        setThoughts(prev => [...prev, thought]);
        setCurrentTier(thought.tier);
        setIsThinking(true);
    }, []);

    const setTier = useCallback((tier: CognitiveTier) => {
        setCurrentTier(tier);
    }, []);

    const setThinking = useCallback((thinking: boolean) => {
        setIsThinking(thinking);
    }, []);

    const clearThoughts = useCallback(() => {
        setThoughts([]);
        setCurrentTier('SYSTEM_1');
        setIsThinking(false);
    }, []);

    const setMeetingRef = useCallback((ref: MeetingRefPayload | null) => {
        setPendingMeetingRef(ref);
    }, []);

    const setGraphViz = useCallback((viz: GraphVizPayload | null) => {
        setPendingGraphViz(viz);
    }, []);

    const setCodeBlock = useCallback((block: CodeBlockPayload | null) => {
        setPendingCodeBlock(block);
    }, []);

    const dismissPanelTrigger = useCallback((type: 'meeting_ref' | 'graph_viz' | 'code_block') => {
        switch (type) {
            case 'meeting_ref': setPendingMeetingRef(null); break;
            case 'graph_viz': setPendingGraphViz(null); break;
            case 'code_block': setPendingCodeBlock(null); break;
        }
    }, []);

    /**
     * Process a data payload from the stream and update context state
     */
    const processDataPayload = useCallback((payload: DataPayload) => {
        switch (payload.type) {
            case 'thought':
                addThought({
                    id: payload.id,
                    step: payload.step,
                    content: payload.content,
                    type: payload.stepType,
                    tier: payload.tier,
                    metadata: payload.metadata,
                });
                break;

            case 'meeting_ref':
                setMeetingRef(payload as MeetingRefPayload);
                break;

            case 'graph_viz':
                setGraphViz(payload as GraphVizPayload);
                break;

            case 'code_block':
                setCodeBlock(payload as CodeBlockPayload);
                break;

            case 'tier_switch':
                setTier(payload.to);
                break;
        }
    }, [addThought, setMeetingRef, setGraphViz, setCodeBlock, setTier]);

    const value = useMemo<GlassBoxState>(() => ({
        thoughts,
        currentTier,
        isThinking,
        pendingMeetingRef,
        pendingGraphViz,
        pendingCodeBlock,
        addThought,
        setTier,
        setThinking,
        clearThoughts,
        setMeetingRef,
        setGraphViz,
        setCodeBlock,
        dismissPanelTrigger,
        processDataPayload,
    }), [
        thoughts,
        currentTier,
        isThinking,
        pendingMeetingRef,
        pendingGraphViz,
        pendingCodeBlock,
        addThought,
        setTier,
        setThinking,
        clearThoughts,
        setMeetingRef,
        setGraphViz,
        setCodeBlock,
        dismissPanelTrigger,
        processDataPayload,
    ]);

    return (
        <GlassBoxContext.Provider value={value}>
            {children}
        </GlassBoxContext.Provider>
    );
}

export default GlassBoxProvider;
