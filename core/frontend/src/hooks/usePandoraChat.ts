import { useChat, Message } from '@ai-sdk/react';
import { useLayerStore } from '../store/useLayerStore';
import { useCallback, useEffect, useRef } from 'react';
import { useGlassBoxSafe } from '@/contexts/GlassBoxContext';
import {
    createInitialParserState,
    StreamParserState,
    DataPayload,
    MeetingRefPayload,
    GraphVizPayload,
    CodeBlockPayload,
} from '../utils/streamParser';
import type { ThoughtStep, CognitiveTier } from '../components/chat/ThoughtAccordion';

export interface PandoraChatState {
    // Core chat state from useChat
    messages: Message[];
    input: string;
    isLoading: boolean;
    error: Error | undefined;

    // Actions
    handleInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
    handleSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
    append: (message: Message) => void;
    reload: () => void;
    stop: () => void;
    setInput: (input: string) => void;
}

export const usePandoraChat = (workspaceSlug?: string): PandoraChatState => {
    const { activeLayerIds, getActiveLayerHeaders } = useLayerStore();
    const glassBox = useGlassBoxSafe();

    // Parser state ref for stream processing
    const parserStateRef = useRef<StreamParserState>(createInitialParserState());

    const chat = useChat({
        api: '/api/v1/stream/chat',
        body: {
            workspace_slug: workspaceSlug || 'default',
            mode: 'auto',
            layer_ids: activeLayerIds,
        },
        headers: {
            ...getActiveLayerHeaders(),
        },
        onResponse: (response) => {
            if (response.status === 401) {
                console.error('[usePandoraChat] Unauthorized');
            }
            // Reset parser state on new response
            parserStateRef.current = createInitialParserState();

            // Allow context to clear its own state
            glassBox?.clearThoughts();
        },
        onFinish: () => {
            if (glassBox) glassBox.setThinking(false);
        },
        onError: (error) => {
            console.error('[usePandoraChat] Error:', error);
            if (glassBox) glassBox.setThinking(false);
        },
    });

    // Process stream data when messages update
    useEffect(() => {
        if (!glassBox) return;

        const lastMessage = chat.messages[chat.messages.length - 1];
        if (!lastMessage || lastMessage.role !== 'assistant') return;

        // Check for data annotations (custom data from stream)
        const annotations = (lastMessage as any).annotations;
        if (annotations && Array.isArray(annotations)) {
            for (const annotation of annotations) {
                // Determine if we've already processed this annotation ID to avoid dupes?
                // For now, rely on idempotency or simple processing
                glassBox.processDataPayload(annotation);
            }
        }
    }, [chat.messages, glassBox]);

    return {
        // Core chat state
        messages: chat.messages,
        input: chat.input,
        isLoading: chat.isLoading,
        error: chat.error,

        // Actions
        handleInputChange: chat.handleInputChange,
        handleSubmit: chat.handleSubmit,
        append: chat.append,
        reload: chat.reload,
        stop: chat.stop,
        setInput: chat.setInput,
    };
};

export default usePandoraChat;
