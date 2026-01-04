import React, { useEffect, useRef, useCallback, useState } from 'react';

/**
 * MeetingPlayer - Audio player with waveform visualization
 * 
 * Phase 5.4: Renders meeting audio with synchronized transcript.
 * Uses wavesurfer.js for waveform display and regions for speaker segments.
 * 
 * Props:
 * - fileId: S3 object key or meeting ID for audio source
 * - timestamp: Initial seek position in seconds
 * - title: Optional meeting title
 * - onTimeUpdate: Callback for playback position updates
 */

// Dynamic import for wavesurfer to avoid SSR issues
let WaveSurfer = null;
if (typeof window !== 'undefined') {
    WaveSurfer = require('wavesurfer.js').default;
}

export default function MeetingPlayer({
    fileId,
    timestamp = 0,
    title = 'Meeting Recording',
    onTimeUpdate
}) {
    const containerRef = useRef(null);
    const wavesurferRef = useRef(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [error, setError] = useState(null);

    // Build audio URL from fileId
    const getAudioUrl = useCallback(() => {
        // In production, this would fetch from MinIO/S3 via signed URL
        // For now, use a proxy endpoint
        const baseUrl = import.meta.env?.VITE_CORTEX_URL || 'http://localhost:8000';
        return `${baseUrl}/api/v1/audio/stream/${fileId}`;
    }, [fileId]);

    // Initialize WaveSurfer
    useEffect(() => {
        if (!containerRef.current || !WaveSurfer) return;

        const wavesurfer = WaveSurfer.create({
            container: containerRef.current,
            waveColor: '#6366f1',       // Indigo-500
            progressColor: '#4f46e5',   // Indigo-600
            cursorColor: '#818cf8',     // Indigo-400
            barWidth: 2,
            barGap: 1,
            barRadius: 2,
            height: 64,
            responsive: true,
            normalize: true,
            backend: 'MediaElement',
        });

        wavesurferRef.current = wavesurfer;

        // Event handlers
        wavesurfer.on('ready', () => {
            setIsLoading(false);
            setDuration(wavesurfer.getDuration());

            // Auto-seek to timestamp if provided
            if (timestamp > 0) {
                wavesurfer.seekTo(timestamp / wavesurfer.getDuration());
            }
        });

        wavesurfer.on('play', () => setIsPlaying(true));
        wavesurfer.on('pause', () => setIsPlaying(false));

        wavesurfer.on('audioprocess', () => {
            const time = wavesurfer.getCurrentTime();
            setCurrentTime(time);
            onTimeUpdate?.(time);
        });

        wavesurfer.on('error', (err) => {
            console.error('WaveSurfer error:', err);
            setError('Failed to load audio');
            setIsLoading(false);
        });

        // Load audio
        wavesurfer.load(getAudioUrl());

        // Cleanup
        return () => {
            wavesurfer.destroy();
        };
    }, [fileId, timestamp, getAudioUrl, onTimeUpdate]);

    // Format time as MM:SS
    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    // Toggle play/pause
    const togglePlay = () => {
        wavesurferRef.current?.playPause();
    };

    // Skip forward/backward
    const skip = (seconds) => {
        if (wavesurferRef.current) {
            const current = wavesurferRef.current.getCurrentTime();
            const target = Math.max(0, Math.min(current + seconds, duration));
            wavesurferRef.current.seekTo(target / duration);
        }
    };

    return (
        <div className="meeting-player bg-zinc-900 rounded-lg p-4 my-2 shadow-lg">
            {/* Header */}
            <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center">
                    <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" />
                    </svg>
                </div>
                <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-white truncate">{title}</h4>
                    <p className="text-xs text-zinc-400">Meeting Recording</p>
                </div>
            </div>

            {/* Waveform container */}
            <div
                ref={containerRef}
                className="waveform-container mb-3 rounded overflow-hidden bg-zinc-800"
                style={{ minHeight: '64px' }}
            >
                {isLoading && (
                    <div className="flex items-center justify-center h-16">
                        <div className="animate-pulse text-zinc-500 text-sm">Loading audio...</div>
                    </div>
                )}
                {error && (
                    <div className="flex items-center justify-center h-16">
                        <div className="text-red-400 text-sm">{error}</div>
                    </div>
                )}
            </div>

            {/* Controls */}
            <div className="flex items-center gap-3">
                {/* Skip back */}
                <button
                    onClick={() => skip(-10)}
                    className="p-1.5 text-zinc-400 hover:text-white transition-colors"
                    aria-label="Skip back 10 seconds"
                >
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 18a8 8 0 100-16 8 8 0 000 16zm.707-10.293a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L9.414 11H13a1 1 0 100-2H9.414l1.293-1.293z" />
                    </svg>
                </button>

                {/* Play/Pause */}
                <button
                    onClick={togglePlay}
                    disabled={isLoading || error}
                    className="p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label={isPlaying ? 'Pause' : 'Play'}
                >
                    {isPlaying ? (
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                    ) : (
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                        </svg>
                    )}
                </button>

                {/* Skip forward */}
                <button
                    onClick={() => skip(10)}
                    className="p-1.5 text-zinc-400 hover:text-white transition-colors"
                    aria-label="Skip forward 10 seconds"
                >
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z" />
                    </svg>
                </button>

                {/* Time display */}
                <div className="flex-1 text-right">
                    <span className="text-sm text-zinc-400 font-mono">
                        {formatTime(currentTime)} / {formatTime(duration)}
                    </span>
                </div>
            </div>
        </div>
    );
}
