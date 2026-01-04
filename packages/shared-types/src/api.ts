/**
 * API Request/Response Types
 * Types for communication between Core and Cortex
 */

// ============================================
// Ingestion API Types
// ============================================

export interface ChunkPreview {
    index: number;
    content: string;
    charCount: number;
    tokenCount: number;
    metadata: Record<string, unknown>;
}

export interface ChunkingConfig {
    chunkSize: number;
    chunkOverlap: number;
    splitter: 'recursive' | 'sentence' | 'paragraph';
}

export interface IngestPreviewRequest {
    file: File;
    chunkSize?: number;
    chunkOverlap?: number;
    splitter?: string;
}

export interface IngestPreviewResponse {
    documentId: string;
    filename: string;
    totalChunks: number;
    chunks: ChunkPreview[];
    chunkingConfig: ChunkingConfig;
}

export interface IngestFinalizeRequest {
    documentId: string;
    approvedChunkIndices?: number[];
    editedChunks?: Record<number, string>;
}

export interface IngestFinalizeResponse {
    documentId: string;
    vectorsCreated: number;
    graphJobId?: string;
}

// ============================================
// Vector API Types
// ============================================

export interface VectorChunk {
    id: string;
    content: string;
    embeddingPreview: number[];
    metadata: Record<string, unknown>;
    documentId: string;
    createdAt: string;
}

export interface CollectionStats {
    name: string;
    totalChunks: number;
    dimensions: number;
    storageBytes: number;
    indexType: string;
}

export interface PaginatedChunks {
    chunks: VectorChunk[];
    total: number;
    page: number;
    pageSize: number;
    hasMore: boolean;
}

// ============================================
// Graph API Types
// ============================================

export type SearchType = 'local' | 'global';

export interface Entity {
    id: string;
    name: string;
    type: string;
    description: string;
    sourceDocuments: string[];
}

export interface Relationship {
    id: string;
    sourceId: string;
    targetId: string;
    type: string;
    description: string;
}

export interface Community {
    id: string;
    level: number;
    title: string;
    summary: string;
    entityCount: number;
    keyEntities: string[];
}

export interface GraphIndexRequest {
    documentIds: string[];
    workspaceId: string;
    forceReindex?: boolean;
}

export interface GraphIndexStatus {
    jobId: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress: number;
    entitiesExtracted: number;
    relationshipsExtracted: number;
    communitiesDetected: number;
    error?: string;
}

export interface GraphQueryRequest {
    query: string;
    workspaceId: string;
    searchType?: SearchType;
    topK?: number;
}

export interface GraphQueryResponse {
    query: string;
    searchType: SearchType;
    context: string;
    entities: Entity[];
    relationships: Relationship[];
    communities: Community[];
}

// ============================================
// Research API Types
// ============================================

export type ResearchType = 'basic' | 'comprehensive' | 'regulatory';

export interface ResearchRequest {
    topic: string;
    workspaceId: string;
    researchType?: ResearchType;
    includeSources?: string[];
    maxSources?: number;
}

export interface ResearchTask {
    taskId: string;
    topic: string;
    status: 'pending' | 'researching' | 'synthesizing' | 'completed' | 'failed';
    progress: number;
    currentStep: string;
    sourcesCrawled: number;
    error?: string;
}

export interface ResearchReport {
    taskId: string;
    topic: string;
    summary: string;
    detailedReport: string;
    sources: ResearchSource[];
    keyFindings: string[];
    createdAt: string;
}

export interface ResearchSource {
    url: string;
    title: string;
    relevanceScore: number;
    excerpt: string;
}
