import React, { useEffect, useRef, useState, useCallback } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js';
import { useGlassBoxSafe } from '@/contexts/GlassBoxContext';
import { Play, Pause, User, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { cortexFetch } from '@/utils/cortexApi';

// Transcript segment from GPU worker (Whisper + Pyannote diarization)
interface TranscriptSegment {
    start: number;
    end: number;
    speaker: string;
    text: string;
    confidence?: number;
}

// GPU worker results for meeting audio processing
interface MeetingWorkerResults {
    audioUrl: string | null;
    transcript: TranscriptSegment[];
    processingStatus: 'pending' | 'processing' | 'completed' | 'failed';
    error?: string;
    metadata?: {
        duration: number;
        speakers: string[];
        language?: string;
    };
}

export const MeetingPlayerView: React.FC = () => {
    const glassBox = useGlassBoxSafe();
    const data = glassBox?.pendingMeetingRef;

    const waveformRef = useRef<HTMLDivElement>(null);
    const wavesurfer = useRef<WaveSurfer | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);

    // GPU Worker Results State
    const [workerResults, setWorkerResults] = useState<MeetingWorkerResults | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [fetchError, setFetchError] = useState<string | null>(null);

    /**
     * Fetch GPU worker results from Cortex API
     * 
     * The audio worker (Phase 4B) stores results in MinIO (S3) and metadata in LanceDB/Postgres.
     * This endpoint retrieves:
     * - Signed URL for the audio file
     * - Transcribed text with timestamps (faster-whisper)
     * - Speaker diarization labels (pyannote.audio)
     */
    const fetchGpuWorkerResults = useCallback(async (fileId: string) => {
        setIsLoading(true);
        setFetchError(null);

        try {
            // Fetch meeting data from Cortex API (GPU worker results)
            const response = await cortexFetch(`/api/v1/meetings/${fileId}/results`);

            if (response.ok) {
                const data = await response.json();

                // Map API response to our interface
                const results: MeetingWorkerResults = {
                    audioUrl: data.audio_url || data.audioUrl || null,
                    transcript: (data.transcript || []).map((seg: any) => ({
                        start: seg.start || 0,
                        end: seg.end || 0,
                        speaker: seg.speaker || seg.speaker_label || 'Unknown',
                        text: seg.text || '',
                        confidence: seg.confidence,
                    })),
                    processingStatus: data.status || 'completed',
                    metadata: data.metadata,
                };

                setWorkerResults(results);
            } else if (response.status === 404) {
                // Meeting not found - may still be processing
                setWorkerResults({
                    audioUrl: null,
                    transcript: [],
                    processingStatus: 'pending',
                    error: 'Meeting transcript is being processed...',
                });
            } else {
                throw new Error(`Failed to fetch meeting results: ${response.status}`);
            }
        } catch (err) {
            console.error('[MeetingPlayer] GPU worker fetch error:', err);
            setFetchError(err instanceof Error ? err.message : 'Failed to load meeting');

            // Fallback to mock data for development/demo
            setWorkerResults({
                audioUrl: 'https://actions.google.com/sounds/v1/ambiences/coffee_shop.ogg',
                transcript: [
                    { start: 0, end: 5, speaker: 'Speaker A', text: "All right, let's get started with the quarterly review." },
                    { start: 5, end: 12, speaker: 'Speaker B', text: "Thanks everyone for joining. We have some interesting data to look at today." },
                    { start: 12, end: 20, speaker: 'Speaker A', text: "Excellent. Did we hit the targets for Q3?" },
                    { start: 20, end: 35, speaker: 'Speaker C', text: "We mostly did. Adoption rate is up 15%." },
                ],
                processingStatus: 'completed',
            });
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Fetch GPU worker results when fileId changes
    useEffect(() => {
        if (data?.fileId) {
            fetchGpuWorkerResults(data.fileId);
        }
    }, [data?.fileId, fetchGpuWorkerResults]);

    // Initialize WaveSurfer when audio URL is available
    useEffect(() => {
        if (!waveformRef.current || !workerResults?.audioUrl) return;

        // Initialize WaveSurfer
        const ws = WaveSurfer.create({
            container: waveformRef.current,
            waveColor: '#334155', // slate-700
            progressColor: '#10B981', // os-fast
            cursorColor: '#10B981',
            barWidth: 2,
            barGap: 1,
            height: 64,
            normalize: true,
            url: workerResults.audioUrl,
        });

        const wsRegions = ws.registerPlugin(RegionsPlugin.create());

        ws.on('ready', () => {
            setDuration(ws.getDuration());

            // Auto-seek if timestamp provided
            if (data?.timestamp) {
                ws.setTime(data.timestamp);
            }
        });

        ws.on('audioprocess', (time) => {
            setCurrentTime(time);
        });

        ws.on('play', () => setIsPlaying(true));
        ws.on('pause', () => setIsPlaying(false));

        wavesurfer.current = ws;

        return () => {
            ws.destroy();
        };
    }, [workerResults?.audioUrl, data?.timestamp]);

    // Handle play/pause toggle
    const togglePlayPause = () => {
        if (wavesurfer.current) {
            wavesurfer.current.playPause();
        }
    };

    // Format time helper
    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    if (!data) return null;

    // Loading state
    if (isLoading) {
        return (
            <div className="w-full h-full bg-os-bg flex flex-col items-center justify-center gap-3">
                <Loader2 className="w-8 h-8 text-os-heavy animate-spin" />
                <p className="text-sm text-slate-400">Loading meeting from GPU worker...</p>
            </div>
        );
    }

    // Processing state
    if (workerResults?.processingStatus === 'pending' || workerResults?.processingStatus === 'processing') {
        return (
            <div className="w-full h-full bg-os-bg flex flex-col items-center justify-center gap-3 p-4">
                <Loader2 className="w-8 h-8 text-os-heavy animate-spin" />
                <p className="text-sm text-slate-300">Meeting is being transcribed...</p>
                <p className="text-xs text-slate-500">GPU worker is processing audio with Whisper + Pyannote</p>
                <button
                    onClick={() => data.fileId && fetchGpuWorkerResults(data.fileId)}
                    className="mt-4 px-3 py-1.5 rounded bg-os-surface border border-os-border text-slate-300 text-sm hover:bg-os-surface/80 flex items-center gap-2"
                >
                    <RefreshCw className="w-4 h-4" />
                    Check Status
                </button>
            </div>
        );
    }

    return (
        <div className="w-full h-full bg-os-bg flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-os-border">
                <h2 className="text-white font-bold">{data.meetingMeta?.title || 'Meeting Recording'}</h2>
                <div className="flex items-center gap-4 mt-1 text-xs text-slate-400">
                    <span>{data.meetingMeta?.date || 'Unknown Date'}</span>
                    <span>{data.meetingMeta?.participants || workerResults?.metadata?.speakers?.length || 2} Participants</span>
                    {fetchError && (
                        <span className="text-yellow-500 flex items-center gap-1">
                            <AlertCircle size={12} />
                            Using demo data
                        </span>
                    )}
                </div>
            </div>

            {/* Waveform Player */}
            <div className="p-4 bg-os-surface border-b border-os-border">
                <div ref={waveformRef} className="mb-4" />

                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <button
                            onClick={togglePlayPause}
                            className="p-2 rounded-full bg-os-fast text-white hover:bg-os-fast/90 transition-colors"
                        >
                            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
                        </button>
                        <span className="text-xs font-mono text-os-fast">
                            {formatTime(currentTime)} / {formatTime(duration)}
                        </span>
                    </div>
                </div>
            </div>

            {/* Transcript (from GPU Worker - Linear Scan Aligned Whisper + Pyannote) */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">
                    Transcript {workerResults?.transcript?.length ? `(${workerResults.transcript.length} segments)` : ''}
                </div>

                {workerResults?.transcript?.map((segment, idx) => {
                    const isActive = currentTime >= segment.start && currentTime <= segment.end;
                    return (
                        <div
                            key={idx}
                            onClick={() => wavesurfer.current?.setTime(segment.start)}
                            className={`
                                p-3 rounded-lg border cursor-pointer transition-all
                                ${isActive
                                    ? 'bg-os-fast/10 border-os-fast/30 shadow-[0_0_10px_rgba(16,185,129,0.1)]'
                                    : 'bg-transparent border-transparent hover:bg-os-surface hover:border-os-border'}
                            `}
                        >
                            <div className="flex items-center gap-2 mb-1">
                                <div className={`p-1 rounded bg-slate-800 ${isActive ? 'text-os-fast' : 'text-slate-400'}`}>
                                    <User size={12} />
                                </div>
                                <span className={`text-xs font-bold ${isActive ? 'text-os-fast' : 'text-slate-400'}`}>
                                    {segment.speaker}
                                </span>
                                <span className="text-[10px] text-slate-600 font-mono ml-auto">
                                    {formatTime(segment.start)}
                                </span>
                            </div>
                            <p className={`text-sm leading-relaxed ${isActive ? 'text-slate-100' : 'text-slate-400'}`}>
                                {segment.text}
                            </p>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default MeetingPlayerView;
