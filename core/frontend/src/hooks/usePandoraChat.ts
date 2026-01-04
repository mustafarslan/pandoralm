import { useChat, UIMessage } from '@ai-sdk/react';
import { useLayerStore } from '../store/useLayerStore';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useGlassBoxSafe } from '@/contexts/GlassBoxContext';
import Chat from '@/models/Chat';
import {
    createInitialParserState,
    StreamParserState,
} from '../utils/streamParser';

// Use UIMessage from AI SDK v5
type Message = UIMessage;

export interface PandoraChatState {
    // Core chat state from useChat
    messages: Message[];
    input: string;
    isLoading: boolean;
    error: Error | undefined;
    isHistoryLoaded: boolean;

    // Actions
    handleInputChange: (value: string) => void;
    handleSubmit: () => void;
    setMessages: (messages: Message[]) => void;
    stop: () => void;
    setInput: (input: string) => void;
}

export const usePandoraChat = (workspaceSlug?: string, threadSlug?: string): PandoraChatState => {
    const { activeLayerIds, getActiveLayerHeaders } = useLayerStore();
    const glassBox = useGlassBoxSafe();
    const [isHistoryLoaded, setIsHistoryLoaded] = useState(false);
    const [inputValue, setInputValue] = useState('');
    const lastSavedPromptRef = useRef<string>('');

    // Parser state ref for stream processing
    const parserStateRef = useRef<StreamParserState>(createInitialParserState());

    const chat = useChat({
        chatId: `${workspaceSlug || 'default'}-${threadSlug || 'main'}`,
        onError: (error) => {
            console.error('[usePandoraChat] Error:', error);
            if (glassBox) glassBox.setThinking(false);
        },
    });

    // Load chat history on mount
    useEffect(() => {
        const loadHistory = async () => {
            if (!workspaceSlug || isHistoryLoaded) return;

            try {
                const history = await Chat.history(workspaceSlug, threadSlug);
                if (history && history.length > 0) {
                    const messages = Chat.toMessages(history);
                    chat.setMessages(messages as Message[]);
                    console.log(`[usePandoraChat] Loaded ${messages.length} messages from history`);
                }
            } catch (err) {
                console.error('[usePandoraChat] Failed to load history:', err);
            }
            setIsHistoryLoaded(true);
        };

        loadHistory();
    }, [workspaceSlug, threadSlug, isHistoryLoaded]);

    // Custom submit handler that sends to Cortex and persists
    const handleSubmitWithPersistence = useCallback(async () => {
        if (!inputValue.trim()) return;

        lastSavedPromptRef.current = inputValue;
        glassBox?.clearThoughts();

        try {
            // Send message via Cortex streaming endpoint
            const response = await fetch('/api/v1/stream/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getActiveLayerHeaders(),
                },
                body: JSON.stringify({
                    query: inputValue,
                    workspace_id: workspaceSlug || 'default',
                    mode: 'auto',
                }),
            });

            // Add user message to chat
            const userMsg: Message = {
                id: `user-${Date.now()}`,
                role: 'user',
                content: inputValue,
            };
            chat.setMessages([...chat.messages, userMsg]);
            setInputValue('');

            // Process streaming response
            if (response.body) {
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let assistantContent = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    // Parse Vercel AI SDK protocol (0: for text)
                    for (const line of chunk.split('\n')) {
                        if (line.startsWith('0:')) {
                            try {
                                const text = JSON.parse(line.slice(2));
                                assistantContent += text;
                            } catch { }
                        }
                    }
                }

                // Add assistant message
                const assistantMsg: Message = {
                    id: `assistant-${Date.now()}`,
                    role: 'assistant',
                    content: assistantContent,
                };
                chat.setMessages([...chat.messages, userMsg, assistantMsg]);

                // Persist to database
                if (workspaceSlug) {
                    await Chat.save(workspaceSlug, inputValue, { text: assistantContent }, threadSlug || null);
                    console.log('[usePandoraChat] Saved chat to database');
                }
            }
        } catch (err) {
            console.error('[usePandoraChat] Error:', err);
        }

        if (glassBox) glassBox.setThinking(false);
    }, [inputValue, workspaceSlug, threadSlug, chat.messages, getActiveLayerHeaders, glassBox]);

    // Process stream data when messages update
    useEffect(() => {
        if (!glassBox) return;

        const lastMessage = chat.messages[chat.messages.length - 1];
        if (!lastMessage || lastMessage.role !== 'assistant') return;

        // Check for data annotations (custom data from stream)
        const annotations = (lastMessage as any).annotations;
        if (annotations && Array.isArray(annotations)) {
            for (const annotation of annotations) {
                glassBox.processDataPayload(annotation);
            }
        }
    }, [chat.messages, glassBox]);

    return {
        // Core chat state
        messages: chat.messages,
        input: inputValue,
        isLoading: chat.status === 'streaming' || chat.status === 'submitted',
        error: chat.error,
        isHistoryLoaded,

        // Actions
        handleInputChange: setInputValue,
        handleSubmit: handleSubmitWithPersistence,
        setMessages: chat.setMessages,
        stop: chat.stop,
        setInput: setInputValue,
    };
};

export default usePandoraChat;
