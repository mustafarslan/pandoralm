/**
 * Vercel AI SDK Data Stream Protocol Parser
 * 
 * This module handles parsing of the special stream format used by Vercel AI SDK.
 * 
 * Wire Format:
 * - Text Parts: `0:"text content"\n`
 * - Data Parts (UI Triggers): `2:[{"type": "thought", ...}]\n`
 * - Error Parts: `3:"error message"\n`
 * 
 * We use this to support "Generative UI" - streaming structured data
 * alongside text tokens to trigger UI components like ThoughtAccordion,
 * MeetingPlayer, and GraphExplorer.
 */

import type { ThoughtStep, StepType, CognitiveTier } from '../components/chat/ThoughtAccordion';

// Stream chunk types as per Vercel AI SDK
export const STREAM_TYPES = {
    TEXT: '0',
    FUNCTION_CALL: '1',
    DATA: '2',
    ERROR: '3',
    ASSISTANT_MESSAGE: '4',
    ASSISTANT_CONTROL_DATA: '5',
    DATA_MESSAGE: '6',
    TOOL_CALL: '7',
    TOOL_RESULT: '8',
    TOOL_CALL_STREAMING_START: '9',
    TOOL_CALL_DELTA: 'a',
    FINISH_MESSAGE: 'd',
    FINISH_STEP: 'e',
} as const;

// Data payload types for our custom UI triggers
export type DataPayloadType =
    | 'thought'
    | 'meeting_ref'
    | 'graph_viz'
    | 'code_block'
    | 'citation'
    | 'security_check'
    | 'tier_switch';

export interface ThoughtDataPayload {
    type: 'thought';
    id: string;
    step: string;
    content: string;
    stepType: StepType;
    tier: CognitiveTier;
    metadata?: Record<string, any>;
}

export interface MeetingRefPayload {
    type: 'meeting_ref';
    fileId: string;
    timestamp?: number;
    meetingMeta?: {
        title?: string;
        date?: string;
        participants?: number;
    };
}

export interface GraphVizPayload {
    type: 'graph_viz';
    nodes: Array<{ id: string; label: string; type?: string }>;
    edges: Array<{ source: string; target: string; label?: string }>;
    layerId?: string;
}

export interface CodeBlockPayload {
    type: 'code_block';
    astData: {
        file: string;
        className?: string;
        methodName?: string;
        breadcrumb: string;
    };
}

export interface SecurityCheckPayload {
    type: 'security_check';
    layerId: string;
    accessLevel: 'READ' | 'WRITE' | 'ADMIN' | 'DENIED';
    reason?: string;
}

export interface TierSwitchPayload {
    type: 'tier_switch';
    from: CognitiveTier;
    to: CognitiveTier;
    reason: string;
}

export type DataPayload =
    | ThoughtDataPayload
    | MeetingRefPayload
    | GraphVizPayload
    | CodeBlockPayload
    | SecurityCheckPayload
    | TierSwitchPayload;

export interface ParsedStreamChunk {
    type: keyof typeof STREAM_TYPES;
    content: string | DataPayload[];
    raw: string;
}

/**
 * Parse a single line from the SSE stream
 */
export function parseStreamLine(line: string): ParsedStreamChunk | null {
    if (!line || line.trim() === '') return null;

    // Find the type prefix (single character followed by colon)
    const colonIndex = line.indexOf(':');
    if (colonIndex === -1 || colonIndex > 1) return null;

    const typeChar = line.charAt(0);
    const content = line.slice(colonIndex + 1);

    try {
        if (typeChar === STREAM_TYPES.TEXT) {
            // Text chunk: 0:"Hello world"
            return {
                type: 'TEXT',
                content: JSON.parse(content),
                raw: line,
            };
        } else if (typeChar === STREAM_TYPES.DATA) {
            // Data chunk: 2:[{...}]
            const parsed = JSON.parse(content);
            return {
                type: 'DATA',
                content: Array.isArray(parsed) ? parsed : [parsed],
                raw: line,
            };
        } else if (typeChar === STREAM_TYPES.ERROR) {
            // Error chunk: 3:"error message"
            return {
                type: 'ERROR',
                content: JSON.parse(content),
                raw: line,
            };
        } else if (typeChar === STREAM_TYPES.TOOL_CALL) {
            // Tool call: 7:{...}
            return {
                type: 'TOOL_CALL',
                content: JSON.parse(content),
                raw: line,
            };
        } else if (typeChar === STREAM_TYPES.FINISH_MESSAGE || typeChar === STREAM_TYPES.FINISH_STEP) {
            // Finish signals
            return {
                type: typeChar === STREAM_TYPES.FINISH_MESSAGE ? 'FINISH_MESSAGE' : 'FINISH_STEP',
                content: content ? JSON.parse(content) : '',
                raw: line,
            };
        }
    } catch (e) {
        console.warn('[StreamParser] Failed to parse line:', line, e);
    }

    return null;
}

/**
 * Convert a ThoughtDataPayload to a ThoughtStep for the accordion
 */
export function dataPayloadToThoughtStep(payload: ThoughtDataPayload): ThoughtStep {
    return {
        id: payload.id,
        step: payload.step,
        content: payload.content,
        type: payload.stepType,
        tier: payload.tier,
        metadata: payload.metadata,
    };
}

/**
 * Stream parser state manager for use in React hooks
 */
export interface StreamParserState {
    textContent: string;
    thoughts: ThoughtStep[];
    dataPayloads: DataPayload[];
    currentTier: CognitiveTier;
    isThinking: boolean;
    error: string | null;
}

export function createInitialParserState(): StreamParserState {
    return {
        textContent: '',
        thoughts: [],
        dataPayloads: [],
        currentTier: 'SYSTEM_1',
        isThinking: false,
        error: null,
    };
}

/**
 * Process a stream chunk and update the parser state
 */
export function processStreamChunk(
    state: StreamParserState,
    chunk: ParsedStreamChunk
): StreamParserState {
    const newState = { ...state };

    switch (chunk.type) {
        case 'TEXT':
            newState.textContent += chunk.content as string;
            break;

        case 'DATA':
            const payloads = chunk.content as DataPayload[];
            for (const payload of payloads) {
                if (payload.type === 'thought') {
                    const thoughtPayload = payload as ThoughtDataPayload;
                    newState.thoughts = [
                        ...newState.thoughts,
                        dataPayloadToThoughtStep(thoughtPayload),
                    ];
                    newState.currentTier = thoughtPayload.tier;
                    newState.isThinking = true;
                } else if (payload.type === 'tier_switch') {
                    newState.currentTier = (payload as TierSwitchPayload).to;
                } else {
                    newState.dataPayloads = [...newState.dataPayloads, payload];
                }
            }
            break;

        case 'ERROR':
            newState.error = chunk.content as string;
            newState.isThinking = false;
            break;

        case 'FINISH_MESSAGE':
        case 'FINISH_STEP':
            newState.isThinking = false;
            break;
    }

    return newState;
}

/**
 * Parse a full SSE stream response (for testing or batch processing)
 */
export function parseFullStream(streamText: string): StreamParserState {
    const lines = streamText.split('\n');
    let state = createInitialParserState();

    for (const line of lines) {
        const chunk = parseStreamLine(line);
        if (chunk) {
            state = processStreamChunk(state, chunk);
        }
    }

    return state;
}
