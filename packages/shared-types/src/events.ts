/**
 * WebSocket Event Types
 * Real-time event definitions for Core <-> Client communication
 */

// ============================================
// Base Event Types
// ============================================

export interface BaseEvent {
    type: string;
    timestamp: string;
}

// ============================================
// Job Progress Events
// ============================================

export interface JobProgressEvent extends BaseEvent {
    type: 'job:progress';
    jobId: string;
    jobType: string;
    progress: number;
    status: string;
    message: string;
}

export interface JobCompletedEvent extends BaseEvent {
    type: 'job:completed';
    jobId: string;
    jobType: string;
    result: Record<string, unknown>;
}

export interface JobFailedEvent extends BaseEvent {
    type: 'job:failed';
    jobId: string;
    jobType: string;
    error: string;
}

// ============================================
// Research Events (SSE)
// ============================================

export interface ResearchStepEvent extends BaseEvent {
    type: 'research:step';
    taskId: string;
    step: string;
    progress: number;
}

export interface ResearchSourceEvent extends BaseEvent {
    type: 'research:source';
    taskId: string;
    url: string;
    title: string;
    status: 'crawling' | 'completed' | 'failed';
}

export interface ResearchCompleteEvent extends BaseEvent {
    type: 'research:complete';
    taskId: string;
    reportId: string;
}

// ============================================
// Graph Indexing Events
// ============================================

export interface GraphIndexingProgressEvent extends BaseEvent {
    type: 'graph:progress';
    jobId: string;
    phase: 'extracting_entities' | 'extracting_relationships' | 'detecting_communities' | 'storing';
    entitiesCount: number;
    relationshipsCount: number;
    communitiesCount: number;
    progress: number;
}

// ============================================
// Chat Streaming Events
// ============================================

export interface ChatChunkEvent extends BaseEvent {
    type: 'chat:chunk';
    threadId: string;
    messageId: string;
    content: string;
}

export interface ChatSourcesEvent extends BaseEvent {
    type: 'chat:sources';
    threadId: string;
    messageId: string;
    sources: Array<{
        documentId: string;
        documentName: string;
        content: string;
        score: number;
    }>;
}

export interface ChatCompleteEvent extends BaseEvent {
    type: 'chat:complete';
    threadId: string;
    messageId: string;
    totalTokens: number;
}

// ============================================
// Union Type for All Events
// ============================================

export type PandoraEvent =
    | JobProgressEvent
    | JobCompletedEvent
    | JobFailedEvent
    | ResearchStepEvent
    | ResearchSourceEvent
    | ResearchCompleteEvent
    | GraphIndexingProgressEvent
    | ChatChunkEvent
    | ChatSourcesEvent
    | ChatCompleteEvent;
