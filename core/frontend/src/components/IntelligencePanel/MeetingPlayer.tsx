import React, { useRef, useEffect } from 'react';
import { Play, Pause, FastForward, Rewind } from 'lucide-react';

interface MeetingPlayerProps {
    data: {
        meetingId: string;
        videoUrl: string;
        transcript: Array<{ start: number; text: string; speaker: string }>;
        timestamp: number;
    };
}

export const MeetingPlayer: React.FC<MeetingPlayerProps> = ({ data }) => {
    const videoRef = useRef<HTMLVideoElement>(null);

    useEffect(() => {
        if (videoRef.current && data.timestamp) {
            videoRef.current.currentTime = data.timestamp;
        }
    }, [data.timestamp]);

    return (
        <div className="flex flex-col h-full bg-[#252525] text-[#CFCFCF] border-l border-[#545454]">
            {/* Header */}
            <div className="p-4 border-b border-[#545454] bg-[#252525]">
                <h3 className="text-sm font-bold uppercase tracking-widest text-[#CFCFCF]">
                    Meeting Intelligence
                </h3>
                <p className="text-xs text-[#7D7D7D] font-mono mt-1">ID: {data.meetingId}</p>
            </div>

            {/* Video Player (Monochrome Container) */}
            <div className="relative bg-black w-full aspect-video flex-shrink-0">
                <video
                    ref={videoRef}
                    src={data.videoUrl}
                    className="w-full h-full object-contain opacity-90 grayscale-[0.2]"
                    controls
                />
            </div>

            {/* Transcript (Ink Wash Style) */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#F2F2F2]">
                {data.transcript.map((segment, idx) => (
                    <div
                        key={idx}
                        className="group flex gap-3 p-3 rounded-lg hover:bg-white border border-transparent hover:border-[#CFCFCF] transition-all cursor-pointer"
                        onClick={() => {
                            if (videoRef.current) videoRef.current.currentTime = segment.start;
                        }}
                    >
                        <div className="min-w-[60px]">
                            <span className="text-xs font-bold text-[#252525] uppercase bg-[#E5E5E5] px-1.5 py-0.5 rounded">
                                {segment.speaker}
                            </span>
                            <p className="text-[10px] text-[#7D7D7D] font-mono mt-1">
                                {new Date(segment.start * 1000).toISOString().substr(14, 5)}
                            </p>
                        </div>
                        <p className="text-sm text-[#252525] leading-relaxed font-medium">
                            {segment.text}
                        </p>
                    </div>
                ))}
            </div>
        </div>
    );
};
