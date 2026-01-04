import React, { useRef, useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { useResizeDetector } from 'react-resize-detector';
import { useGlassBoxSafe } from '@/contexts/GlassBoxContext';

interface GraphNode {
    id: string;
    group?: number;
    val?: number; // size
    label?: string;
    color?: string;
}

interface GraphLink {
    source: string;
    target: string;
    width?: number;
    color?: string;
}

interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

export const GraphExplorerView: React.FC = () => {
    const glassBox = useGlassBoxSafe();
    const data = glassBox?.pendingGraphViz;
    const { width, height, ref } = useResizeDetector();
    const graphRef = useRef<any>();

    // Transform API data to graph format if needed
    // Assuming data coming from glassBox matches or needs simple mapping
    const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });

    useEffect(() => {
        if (data) {
            setGraphData({
                nodes: data.nodes.map(n => ({
                    id: n.id,
                    label: n.label,
                    color: n.type === 'concept' ? '#8B5CF6' : '#10B981', // Violet vs Emerald
                    val: 5
                })),
                links: data.edges.map(e => ({
                    source: e.source,
                    target: e.target,
                    color: 'rgba(255,255,255,0.2)'
                }))
            });
        }
    }, [data]);

    return (
        <div ref={ref} className="w-full h-full bg-os-bg relative">
            {!data && (
                <div className="absolute inset-0 flex items-center justify-center text-slate-500 text-sm">
                    No graph data available
                </div>
            )}
            {data && width && height && (
                <ForceGraph2D
                    ref={graphRef}
                    width={width}
                    height={height}
                    graphData={graphData}
                    nodeLabel="label"
                    nodeColor="color"
                    linkColor="color"
                    backgroundColor="#05070A" // os-bg
                    d3AlphaDecay={0.1} // slower decay for smoother stabilization
                    d3VelocityDecay={0.3} // reduce jitter
                />
            )}

            {/* Legend or Controls could go here */}
            <div className="absolute bottom-4 left-4 p-2 bg-os-surface/80 backdrop-blur rounded border border-os-border text-xs text-slate-400">
                <div className="flex items-center gap-2 mb-1">
                    <div className="w-2 h-2 rounded-full bg-os-heavy"></div>
                    <span>Concept</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-os-fast"></div>
                    <span>Entity</span>
                </div>
            </div>
        </div>
    );
};

export default GraphExplorerView;
