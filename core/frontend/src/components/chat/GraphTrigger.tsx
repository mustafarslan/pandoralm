import React from 'react';
import { Network, ExternalLink } from 'lucide-react';

interface GraphTriggerProps {
    nodeCount?: number;
    edgeCount?: number;
    layerId?: string;
    onClick?: () => void;
}

/**
 * GraphTrigger - A clickable card that triggers the Graph Explorer in the side panel
 * 
 * This component is rendered inline in the chat when the AI uses GraphRAG.
 * Clicking it opens the IntelligenceSidePanel in GRAPH mode.
 */
const GraphTrigger: React.FC<GraphTriggerProps> = ({
    nodeCount = 0,
    edgeCount = 0,
    layerId,
    onClick,
}) => {
    return (
        <div
            onClick={onClick}
            className="
                inline-flex items-center gap-2 bg-os-surface border border-os-border
                rounded-lg px-3 py-2 my-1 hover:border-os-heavy transition-all
                cursor-pointer group text-sm
            "
        >
            {/* Graph Icon */}
            <div className="p-1.5 bg-os-heavy/10 text-os-heavy rounded-lg group-hover:bg-os-heavy group-hover:text-white transition-all">
                <Network size={16} />
            </div>

            {/* Info */}
            <div className="flex items-center gap-3 text-slate-300">
                <span className="font-medium">Knowledge Graph</span>
                {nodeCount > 0 && (
                    <span className="text-[10px] text-slate-500 font-mono">
                        {nodeCount} nodes • {edgeCount} edges
                    </span>
                )}
            </div>

            {/* Arrow */}
            <ExternalLink size={14} className="text-slate-500 group-hover:text-os-heavy transition-colors" />
        </div>
    );
};

export default GraphTrigger;
