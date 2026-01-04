/**
 * GraphViewer Component
 * Interactive knowledge graph visualization using Cytoscape.js
 */
import React, { useEffect, useRef, useState } from 'react';

// Types for graph data
interface GraphNode {
    id: string;
    label: string;
    type: string;
    description: string;
    size?: number;
}

interface GraphEdge {
    id: string;
    source: string;
    target: string;
    label: string;
    weight?: number;
}

interface GraphData {
    nodes: GraphNode[];
    edges: GraphEdge[];
    stats: {
        total_nodes: number;
        total_edges: number;
        entity_types: Record<string, number>;
    };
}

interface GraphViewerProps {
    workspaceId: string;
    apiBaseUrl?: string;
    onNodeClick?: (node: GraphNode) => void;
    onEdgeClick?: (edge: GraphEdge) => void;
    height?: string;
    entityTypeFilter?: string[];
}

// Color palette for entity types
const TYPE_COLORS: Record<string, string> = {
    PERSON: '#f59e0b',
    ORGANIZATION: '#10b981',
    CONCEPT: '#8b5cf6',
    REGULATION: '#ef4444',
    TECHNOLOGY: '#3b82f6',
    LOCATION: '#06b6d4',
    EVENT: '#ec4899',
    DOCUMENT: '#6366f1',
    OTHER: '#94a3b8',
};

export const GraphViewer: React.FC<GraphViewerProps> = ({
    workspaceId,
    apiBaseUrl = '/api/v1',
    onNodeClick,
    onEdgeClick,
    height = '600px',
    entityTypeFilter,
}) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const cyRef = useRef<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [stats, setStats] = useState<GraphData['stats'] | null>(null);

    useEffect(() => {
        loadGraph();
    }, [workspaceId, entityTypeFilter]);

    const loadGraph = async () => {
        setLoading(true);
        setError(null);

        try {
            // Build query params
            const params = new URLSearchParams();
            if (entityTypeFilter?.length) {
                params.set('entity_types', entityTypeFilter.join(','));
            }

            const response = await fetch(
                `${apiBaseUrl}/viz/${workspaceId}?${params}`
            );

            if (!response.ok) {
                throw new Error(`Failed to load graph: ${response.statusText}`);
            }

            const data: GraphData = await response.json();
            setStats(data.stats);

            // Initialize Cytoscape
            await initializeCytoscape(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load graph');
        } finally {
            setLoading(false);
        }
    };

    const initializeCytoscape = async (data: GraphData) => {
        // Dynamically import cytoscape
        const cytoscape = (await import('cytoscape')).default;

        if (!containerRef.current) return;

        // Destroy existing instance
        if (cyRef.current) {
            cyRef.current.destroy();
        }

        // Build elements
        const elements = [
            // Nodes
            ...data.nodes.map((node) => ({
                data: {
                    id: node.id,
                    label: node.label,
                    type: node.type,
                    description: node.description,
                },
                classes: node.type.toLowerCase(),
            })),
            // Edges
            ...data.edges.map((edge) => ({
                data: {
                    id: edge.id,
                    source: edge.source,
                    target: edge.target,
                    label: edge.label,
                    weight: edge.weight || 1,
                },
            })),
        ];

        // Create Cytoscape instance
        cyRef.current = cytoscape({
            container: containerRef.current,
            elements,
            style: [
                {
                    selector: 'node',
                    style: {
                        label: 'data(label)',
                        'background-color': '#6366f1',
                        color: '#fff',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'font-size': '10px',
                        width: '40px',
                        height: '40px',
                        'text-wrap': 'ellipsis',
                        'text-max-width': '80px',
                    },
                },
                // Type-specific colors
                ...Object.entries(TYPE_COLORS).map(([type, color]) => ({
                    selector: `node.${type.toLowerCase()}`,
                    style: { 'background-color': color },
                })),
                {
                    selector: 'edge',
                    style: {
                        width: 2,
                        'line-color': '#94a3b8',
                        'target-arrow-color': '#94a3b8',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        label: 'data(label)',
                        'font-size': '8px',
                        'text-rotation': 'autorotate',
                        color: '#64748b',
                    },
                },
                {
                    selector: ':selected',
                    style: {
                        'border-width': 3,
                        'border-color': '#1e40af',
                    },
                },
            ],
            layout: {
                name: 'cose',
                animate: true,
                animationDuration: 500,
                nodeRepulsion: () => 8000,
                idealEdgeLength: () => 100,
            },
        });

        // Event handlers
        cyRef.current.on('tap', 'node', (event: any) => {
            const node = event.target.data();
            onNodeClick?.(node);
        });

        cyRef.current.on('tap', 'edge', (event: any) => {
            const edge = event.target.data();
            onEdgeClick?.(edge);
        });
    };

    const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.2);
    const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() / 1.2);
    const handleFit = () => cyRef.current?.fit();
    const handleCenter = () => cyRef.current?.center();

    return (
        <div className="graph-viewer" style={{ position: 'relative' }}>
            {/* Controls */}
            <div
                style={{
                    position: 'absolute',
                    top: 10,
                    right: 10,
                    zIndex: 10,
                    display: 'flex',
                    gap: '8px',
                }}
            >
                <button onClick={handleZoomIn} title="Zoom In">+</button>
                <button onClick={handleZoomOut} title="Zoom Out">−</button>
                <button onClick={handleFit} title="Fit">⊡</button>
                <button onClick={handleCenter} title="Center">◎</button>
                <button onClick={loadGraph} title="Refresh">↻</button>
            </div>

            {/* Stats */}
            {stats && (
                <div
                    style={{
                        position: 'absolute',
                        top: 10,
                        left: 10,
                        zIndex: 10,
                        background: 'rgba(0,0,0,0.7)',
                        color: '#fff',
                        padding: '8px 12px',
                        borderRadius: '4px',
                        fontSize: '12px',
                    }}
                >
                    <div>Nodes: {stats.total_nodes}</div>
                    <div>Edges: {stats.total_edges}</div>
                </div>
            )}

            {/* Loading */}
            {loading && (
                <div
                    style={{
                        position: 'absolute',
                        inset: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: 'rgba(255,255,255,0.8)',
                        zIndex: 20,
                    }}
                >
                    Loading graph...
                </div>
            )}

            {/* Error */}
            {error && (
                <div
                    style={{
                        position: 'absolute',
                        inset: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: 'rgba(255,255,255,0.9)',
                        color: '#ef4444',
                        zIndex: 20,
                    }}
                >
                    {error}
                </div>
            )}

            {/* Graph container */}
            <div
                ref={containerRef}
                style={{
                    width: '100%',
                    height,
                    background: '#1e293b',
                    borderRadius: '8px',
                }}
            />

            {/* Legend */}
            <div
                style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '12px',
                    marginTop: '12px',
                    fontSize: '12px',
                }}
            >
                {Object.entries(TYPE_COLORS).map(([type, color]) => (
                    <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <span
                            style={{
                                width: 12,
                                height: 12,
                                borderRadius: '50%',
                                background: color,
                            }}
                        />
                        <span>{type}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default GraphViewer;
