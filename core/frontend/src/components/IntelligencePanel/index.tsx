import React from 'react';
import { X, Network, PlayCircle, Code2 } from 'lucide-react';
import { MeetingPlayer } from '../IntelligencePanel/MeetingPlayer';
import { GraphView } from '../IntelligencePanel/GraphView';
import { CodeViewer } from '../IntelligencePanel/CodeViewer';

export type IntelligenceMode = 'CLOSED' | 'GRAPH' | 'MEETING' | 'CODE';

interface IntelligenceSidePanelProps {
    mode: IntelligenceMode;
    data: any;
    onClose: () => void;
    layerId?: string;
}

export const IntelligenceSidePanel: React.FC<IntelligenceSidePanelProps> = ({
    mode,
    data,
    onClose,
    layerId = "system_public"
}) => {
    if (mode === 'CLOSED') return null;

    return (
        <div className="w-[450px] h-full bg-[#FAFAFA] border-l border-[#CFCFCF] flex flex-col shadow-xl animate-slide-in-right">
            {/* Panel Header */}
            <div className="p-4 border-b border-[#CFCFCF] flex items-center justify-between bg-white">
                <div className="flex items-center gap-2">
                    {mode === 'GRAPH' && <Network className="w-5 h-5 text-[#252525]" />}
                    {mode === 'MEETING' && <PlayCircle className="w-5 h-5 text-[#252525]" />}
                    {mode === 'CODE' && <Code2 className="w-5 h-5 text-[#252525]" />}
                    <span className="text-xs font-bold uppercase tracking-widest text-[#545454]">
                        {mode} Intelligence
                    </span>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 hover:bg-[#F2F2F2] rounded text-[#7D7D7D] hover:text-[#252525] transition-colors"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>

            {/* Dynamic Content Area */}
            <div className="flex-1 overflow-hidden relative">
                {mode === 'GRAPH' && <GraphView data={data} />}
                {mode === 'MEETING' && <MeetingPlayer data={data} />}
                {mode === 'CODE' && <CodeViewer data={data} />}
            </div>

            {/* ReBAC Access Badge */}
            <div className="p-3 bg-[#F2F2F2] border-t border-[#CFCFCF] flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[#252525] shadow-[0_0_2px_#252525]" />
                <span className="text-[10px] text-[#545454] font-mono">
                    LAYER_ID: {layerId}
                </span>
            </div>
        </div>
    );
};
