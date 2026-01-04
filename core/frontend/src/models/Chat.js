/**
 * Chat Model - Frontend API for chat history persistence
 * 
 * Provides methods for loading and saving chat messages to the backend,
 * enabling chat history persistence across navigation.
 */

import { API_BASE } from '@/utils/constants';

const Chat = {
    /**
     * Get chat history for a workspace/thread
     * @param {string} workspaceSlug - Workspace slug
     * @param {string|null} threadSlug - Optional thread slug
     * @returns {Promise<Array>} Array of chat messages
     */
    history: async function (workspaceSlug, threadSlug = null) {
        const params = new URLSearchParams();
        if (threadSlug) params.append('threadSlug', threadSlug);

        const response = await fetch(
            `${API_BASE}/v1/workspace/${workspaceSlug}/chats?${params.toString()}`,
            {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
            }
        );

        if (!response.ok) {
            console.error('[Chat.history] Failed to load chat history');
            return [];
        }

        const data = await response.json();
        return data.history || [];
    },

    /**
     * Save a chat message pair (user prompt + AI response)
     * @param {string} workspaceSlug - Workspace slug
     * @param {string} prompt - User's message
     * @param {object} response - AI response object
     * @param {string|null} threadId - Optional thread ID
     * @returns {Promise<object>} Saved chat record
     */
    save: async function (workspaceSlug, prompt, responseObj, threadId = null) {
        const response = await fetch(
            `${API_BASE}/v1/workspace/${workspaceSlug}/chats`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    prompt,
                    response: responseObj,
                    threadId,
                }),
            }
        );

        if (!response.ok) {
            console.error('[Chat.save] Failed to save chat message');
            return null;
        }

        return response.json();
    },

    /**
     * Format backend chat records to Vercel AI SDK Message format
     * @param {Array} history - Raw chat records from backend
     * @returns {Array} Messages in AI SDK format
     */
    toMessages: function (history) {
        const messages = [];

        for (const record of history) {
            // User message
            messages.push({
                id: `user-${record.id}`,
                role: 'user',
                content: record.prompt,
                createdAt: new Date(record.createdAt),
            });

            // Assistant message (response is JSON stringified)
            let assistantContent = '';
            try {
                const resp = typeof record.response === 'string'
                    ? JSON.parse(record.response)
                    : record.response;
                assistantContent = resp.text || resp.content || '';
            } catch {
                assistantContent = record.response || '';
            }

            if (assistantContent) {
                messages.push({
                    id: `assistant-${record.id}`,
                    role: 'assistant',
                    content: assistantContent,
                    createdAt: new Date(record.createdAt),
                });
            }
        }

        return messages;
    },
};

export default Chat;
