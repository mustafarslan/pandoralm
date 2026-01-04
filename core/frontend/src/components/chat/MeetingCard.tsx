import React from 'react';
import { PlayCircle, Calendar, Users, Clock } from 'lucide-react';

interface MeetingMeta {
    title?: string;
    date?: string;
    participants?: number;
    duration?: string;
}

interface MeetingCardProps {
    id: string;
    timestamp?: number;
    meeting_meta?: MeetingMeta;
    onClick?: (id: string, timestamp?: number) => void;
}

/**
 * MeetingCard - A clickable card that triggers the Meeting Player in the side panel
 * 
 * This component is rendered inline in the chat when the AI references a meeting.
 * Clicking it opens the IntelligenceSidePanel in MEETING mode.
 */
const MeetingCard: React.FC<MeetingCardProps> = ({ id, timestamp, meeting_meta, onClick }) => {
    const handleClick = () => {
        onClick?.(id, timestamp);
    };

    return (
        <div
            onClick={handleClick}
            className="
                bg-os-surface border border-os-border rounded-xl p-4 my-2 max-w-sm
                hover:border-os-fast transition-all cursor-pointer group
                shadow-lg hover:shadow-[0_0_20px_rgba(16,185,129,0.15)]
            "
        >
            <div className="flex items-start gap-3">
                {/* Play Icon */}
                <div className="p-2.5 bg-os-fast/10 text-os-fast rounded-xl group-hover:bg-os-fast group-hover:text-white transition-all">
                    <PlayCircle size={24} />
                </div>

                <div className="flex-1 min-w-0">
                    {/* Title */}
                    <h3 className="font-semibold text-slate-100 text-sm truncate">
                        {meeting_meta?.title || 'Meeting Recording'}
                    </h3>

                    {/* Meta Info */}
                    <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                        <span className="flex items-center gap-1">
                            <Calendar size={12} />
                            {meeting_meta?.date || 'Today'}
                        </span>
                        <span className="flex items-center gap-1">
                            <Users size={12} />
                            {meeting_meta?.participants || 2} participants
                        </span>
                        {meeting_meta?.duration && (
                            <span className="flex items-center gap-1">
                                <Clock size={12} />
                                {meeting_meta.duration}
                            </span>
                        )}
                    </div>

                    {/* Timestamp indicator */}
                    {timestamp !== undefined && timestamp > 0 && (
                        <div className="mt-2 text-[10px] text-os-fast font-mono">
                            Jump to {formatTimestamp(timestamp)}
                        </div>
                    )}

                    {/* CTA */}
                    <div className="mt-3 text-xs bg-os-bg/50 p-2 rounded-lg text-slate-400 group-hover:text-os-fast transition-colors">
                        Click to open Meeting Player
                    </div>
                </div>
            </div>
        </div>
    );
};

/**
 * Format timestamp in seconds to MM:SS or HH:MM:SS
 */
function formatTimestamp(seconds: number): string {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hrs > 0) {
        return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default MeetingCard;
