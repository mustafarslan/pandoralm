import React, { useRef, useEffect } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

interface GraphViewProps {
    data: {
        nodes: Array<{ id: string; group: number; label: string }>;
        links: Array<{ source: string; target: string; value: number }>;
    };
}

export const GraphView: React.FC<GraphViewProps> = ({ data }) => {
    const containerRef = useRef<HTMLDivElement>(null);

    return (
        <div className="flex flex-col h-full bg-[#252525] text-[#CFCFCF] border-l border-[#545454]">
            {/* Header */}
            <div className="p-4 border-b border-[#545454] bg-[#252525] z-10">
                <h3 className="text-sm font-bold uppercase tracking-widest text-[#CFCFCF]">
                    Global Search
                </h3>
                <p className="text-xs text-[#7D7D7D] font-mono mt-1">
                    {data.nodes.length} Communities • {data.links.length} Relationships
                </p>
            </div>

            <div ref={containerRef} className="flex-1 overflow-hidden relative bg-[#252525]">
                <ForceGraph2D
                    width={450} // Fixed width for panel, ideally dynamic
                    height={600}
                    graphData={data}
                    backgroundColor="#252525"
                    nodeColor={() => "#FFFFFF"} // White Nodes
                    nodeLabel="label"
                    linkColor={() => "#7D7D7D"} // Stone Edges
                    linkWidth={1}
                    nodeRelSize={4}
                    d3AlphaDecay={0.05}
                    onNodeClick={(node) => {
                        // Future: Open side sheet
                        console.log("Clicked node:", node);
                    }}
                />

                {/* Overlay Controls */}
                <div className="absolute bottom-4 right-4 flex flex-col gap-2">
                    <button className="p-2 bg-[#545454] rounded text-white hover:bg-white hover:text-black transition-colors">
                        <span className="text-xs font-bold">+</span>
                    </button>
                    <button className="p-2 bg-[#545454] rounded text-white hover:bg-white hover:text-black transition-colors">
                        <span className="text-xs font-bold">-</span>
                    </button>
                </div>
            </div>
        </div>
    );
};
