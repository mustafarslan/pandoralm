/**
 * ChunkInspector Component
 * View, edit, and manage vector chunks
 */
import React, { useState, useEffect } from 'react';

interface Chunk {
    id: string;
    content: string;
    document_id: string;
    metadata: Record<string, any>;
    created_at: string;
    embedding_preview: number[];
}

interface ChunkInspectorProps {
    workspaceId: string;
    documentId?: string;
    apiBaseUrl?: string;
    onChunkSelect?: (chunk: Chunk) => void;
    onChunkEdit?: (chunkId: string, newContent: string) => void;
    onChunkDelete?: (chunkId: string) => void;
}

export const ChunkInspector: React.FC<ChunkInspectorProps> = ({
    workspaceId,
    documentId,
    apiBaseUrl = '/api/v1',
    onChunkSelect,
    onChunkEdit,
    onChunkDelete,
}) => {
    const [chunks, setChunks] = useState<Chunk[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(false);
    const [total, setTotal] = useState(0);
    const [selectedChunk, setSelectedChunk] = useState<Chunk | null>(null);
    const [editContent, setEditContent] = useState('');
    const [isEditing, setIsEditing] = useState(false);

    useEffect(() => {
        loadChunks();
    }, [workspaceId, documentId, page]);

    const loadChunks = async () => {
        setLoading(true);
        setError(null);

        try {
            const params = new URLSearchParams({
                page: page.toString(),
                page_size: '20',
            });
            if (documentId) {
                params.set('document_id', documentId);
            }

            const response = await fetch(
                `${apiBaseUrl}/vectors/collections/${workspaceId}/chunks?${params}`
            );

            if (!response.ok) {
                throw new Error(`Failed to load chunks: ${response.statusText}`);
            }

            const data = await response.json();
            setChunks(data.chunks);
            setHasMore(data.has_more);
            setTotal(data.total);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load chunks');
        } finally {
            setLoading(false);
        }
    };

    const handleSelectChunk = (chunk: Chunk) => {
        setSelectedChunk(chunk);
        setEditContent(chunk.content);
        setIsEditing(false);
        onChunkSelect?.(chunk);
    };

    const handleSaveEdit = async () => {
        if (!selectedChunk) return;

        try {
            const response = await fetch(
                `${apiBaseUrl}/vectors/chunks/${workspaceId}/${selectedChunk.id}`,
                {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        content: editContent,
                        re_embed: true,
                    }),
                }
            );

            if (!response.ok) {
                throw new Error('Failed to update chunk');
            }

            onChunkEdit?.(selectedChunk.id, editContent);
            setIsEditing(false);
            loadChunks(); // Refresh
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Update failed');
        }
    };

    const handleDelete = async (chunkId: string) => {
        if (!confirm('Are you sure you want to delete this chunk?')) return;

        try {
            const response = await fetch(
                `${apiBaseUrl}/vectors/chunks/${workspaceId}/${chunkId}`,
                { method: 'DELETE' }
            );

            if (!response.ok) {
                throw new Error('Failed to delete chunk');
            }

            onChunkDelete?.(chunkId);
            if (selectedChunk?.id === chunkId) {
                setSelectedChunk(null);
            }
            loadChunks(); // Refresh
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Delete failed');
        }
    };

    return (
        <div className="chunk-inspector" style={{ display: 'flex', gap: '20px' }}>
            {/* Chunk List */}
            <div style={{ flex: 1, maxWidth: '400px' }}>
                <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between' }}>
                    <h3 style={{ margin: 0 }}>Chunks ({total})</h3>
                    <button onClick={loadChunks}>Refresh</button>
                </div>

                {loading && <div>Loading...</div>}
                {error && <div style={{ color: '#ef4444' }}>{error}</div>}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {chunks.map((chunk) => (
                        <div
                            key={chunk.id}
                            onClick={() => handleSelectChunk(chunk)}
                            style={{
                                padding: '12px',
                                background: selectedChunk?.id === chunk.id ? '#e0e7ff' : '#f8fafc',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                border: selectedChunk?.id === chunk.id ? '2px solid #6366f1' : '1px solid #e2e8f0',
                            }}
                        >
                            <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '4px' }}>
                                {chunk.id.slice(0, 20)}...
                            </div>
                            <div style={{ fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {chunk.content.slice(0, 100)}...
                            </div>
                            <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                                {chunk.content.length} chars
                            </div>
                        </div>
                    ))}
                </div>

                {/* Pagination */}
                <div style={{ marginTop: '12px', display: 'flex', gap: '8px', justifyContent: 'center' }}>
                    <button disabled={page === 1} onClick={() => setPage(page - 1)}>
                        Previous
                    </button>
                    <span>Page {page}</span>
                    <button disabled={!hasMore} onClick={() => setPage(page + 1)}>
                        Next
                    </button>
                </div>
            </div>

            {/* Chunk Detail */}
            <div style={{ flex: 2 }}>
                {selectedChunk ? (
                    <div>
                        <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between' }}>
                            <h3 style={{ margin: 0 }}>Chunk Detail</h3>
                            <div style={{ display: 'flex', gap: '8px' }}>
                                {isEditing ? (
                                    <>
                                        <button onClick={handleSaveEdit} style={{ background: '#10b981', color: '#fff' }}>
                                            Save
                                        </button>
                                        <button onClick={() => setIsEditing(false)}>Cancel</button>
                                    </>
                                ) : (
                                    <>
                                        <button onClick={() => setIsEditing(true)}>Edit</button>
                                        <button
                                            onClick={() => handleDelete(selectedChunk.id)}
                                            style={{ background: '#ef4444', color: '#fff' }}
                                        >
                                            Delete
                                        </button>
                                    </>
                                )}
                            </div>
                        </div>

                        {/* Metadata */}
                        <div style={{ marginBottom: '16px', fontSize: '12px', color: '#64748b' }}>
                            <div>ID: {selectedChunk.id}</div>
                            <div>Document: {selectedChunk.document_id}</div>
                            <div>Created: {new Date(selectedChunk.created_at).toLocaleString()}</div>
                        </div>

                        {/* Content */}
                        {isEditing ? (
                            <textarea
                                value={editContent}
                                onChange={(e) => setEditContent(e.target.value)}
                                style={{
                                    width: '100%',
                                    height: '300px',
                                    padding: '12px',
                                    borderRadius: '6px',
                                    border: '1px solid #e2e8f0',
                                    fontFamily: 'monospace',
                                    fontSize: '13px',
                                }}
                            />
                        ) : (
                            <div
                                style={{
                                    padding: '16px',
                                    background: '#f8fafc',
                                    borderRadius: '8px',
                                    whiteSpace: 'pre-wrap',
                                    fontFamily: 'monospace',
                                    fontSize: '13px',
                                    maxHeight: '400px',
                                    overflow: 'auto',
                                }}
                            >
                                {selectedChunk.content}
                            </div>
                        )}

                        {/* Embedding preview */}
                        <div style={{ marginTop: '16px' }}>
                            <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '4px' }}>
                                Embedding Preview (first 5 dims)
                            </div>
                            <div style={{ fontFamily: 'monospace', fontSize: '11px' }}>
                                [{selectedChunk.embedding_preview?.join(', ')}...]
                            </div>
                        </div>
                    </div>
                ) : (
                    <div style={{ color: '#94a3b8', textAlign: 'center', paddingTop: '100px' }}>
                        Select a chunk to view details
                    </div>
                )}
            </div>
        </div>
    );
};

export default ChunkInspector;
