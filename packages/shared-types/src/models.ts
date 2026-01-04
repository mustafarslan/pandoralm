/**
 * Domain Model Types
 * Core business entities for PandoraLM
 */

// ============================================
// User & Auth Models
// ============================================

export interface User {
    id: string;
    keycloakId: string;
    email: string;
    username: string;
    firstName?: string;
    lastName?: string;
    roles: string[];
    groups: string[];
    createdAt: string;
    updatedAt: string;
}

export type UserRole = 'user' | 'admin' | 'vector-ops';

// ============================================
// Workspace Models
// ============================================

export interface Workspace {
    id: string;
    name: string;
    slug: string;
    description?: string;
    ownerId: string;
    teamId?: string;
    settings: WorkspaceSettings;
    createdAt: string;
    updatedAt: string;
}

export interface WorkspaceSettings {
    llmProvider: string;
    llmModel: string;
    embeddingModel: string;
    temperature: number;
    topK: number;
    enableGraphRag: boolean;
    enableDeepResearch: boolean;
}

export interface Team {
    id: string;
    name: string;
    keycloakGroupPath: string;
    members: string[];
    workspaces: string[];
    createdAt: string;
}

// ============================================
// Document Models
// ============================================

export interface Document {
    id: string;
    workspaceId: string;
    filename: string;
    originalPath: string;
    mimeType: string;
    sizeBytes: number;
    status: DocumentStatus;
    chunkCount: number;
    vectorsGenerated: boolean;
    graphIndexed: boolean;
    metadata: Record<string, unknown>;
    createdAt: string;
    updatedAt: string;
}

export type DocumentStatus =
    | 'pending'
    | 'processing'
    | 'chunked'
    | 'embedded'
    | 'indexed'
    | 'failed';

// ============================================
// Chat Models
// ============================================

export interface ChatMessage {
    id: string;
    threadId: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    sources?: ChatSource[];
    searchMode?: 'vector' | 'graph' | 'hybrid';
    createdAt: string;
}

export interface ChatSource {
    documentId: string;
    documentName: string;
    chunkId: string;
    content: string;
    score: number;
}

export interface ChatThread {
    id: string;
    workspaceId: string;
    userId: string;
    title: string;
    messages: ChatMessage[];
    createdAt: string;
    updatedAt: string;
}

// ============================================
// Job Models
// ============================================

export interface BackgroundJob {
    id: string;
    type: JobType;
    status: JobStatus;
    progress: number;
    workspaceId: string;
    metadata: Record<string, unknown>;
    error?: string;
    startedAt: string;
    completedAt?: string;
}

export type JobType =
    | 'document_ingestion'
    | 'vector_embedding'
    | 'graph_indexing'
    | 'vector_reindex'
    | 'deep_research';

export type JobStatus =
    | 'pending'
    | 'running'
    | 'completed'
    | 'failed'
    | 'cancelled';
