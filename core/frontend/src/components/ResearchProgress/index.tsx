/**
 * ResearchProgress Component
 * Real-time research progress display with SSE streaming
 */
import React, { useState, useEffect, useRef } from 'react';

interface ResearchStep {
    status: string;
    progress: number;
    current_step: string;
    sources_found: number;
    message: string;
    timestamp: Date;
}

interface ResearchProgressProps {
    taskId: string;
    apiBaseUrl?: string;
    onComplete?: (taskId: string) => void;
    onError?: (error: string) => void;
}

export const ResearchProgress: React.FC<ResearchProgressProps> = ({
    taskId,
    apiBaseUrl = '/api/v1',
    onComplete,
    onError,
}) => {
    const [steps, setSteps] = useState<ResearchStep[]>([]);
    const [currentProgress, setCurrentProgress] = useState(0);
    const [status, setStatus] = useState<string>('connecting');
    const [error, setError] = useState<string | null>(null);
    const eventSourceRef = useRef<EventSource | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        startStreaming();
        return () => stopStreaming();
    }, [taskId]);

    const startStreaming = () => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }

        const eventSource = new EventSource(`${apiBaseUrl}/research/stream/${taskId}`);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
            setStatus('connected');
            setError(null);
        };

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === 'complete') {
                    setStatus('completed');
                    onComplete?.(taskId);
                    eventSource.close();
                    return;
                }

                const step: ResearchStep = {
                    status: data.status,
                    progress: data.progress,
                    current_step: data.current_step,
                    sources_found: data.sources_found,
                    message: data.message,
                    timestamp: new Date(),
                };

                setSteps((prev) => [...prev, step]);
                setCurrentProgress(data.progress);
                setStatus(data.status);

                // Auto-scroll
                if (containerRef.current) {
                    containerRef.current.scrollTop = containerRef.current.scrollHeight;
                }
            } catch (err) {
                console.error('Failed to parse SSE data', err);
            }
        };

        eventSource.onerror = () => {
            setError('Connection lost');
            onError?.('Connection lost');
            eventSource.close();
        };
    };

    const stopStreaming = () => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
    };

    const getStatusColor = (status: string): string => {
        switch (status) {
            case 'analyzing': return '#f59e0b';
            case 'researching': return '#3b82f6';
            case 'synthesizing': return '#8b5cf6';
            case 'completed': return '#10b981';
            case 'failed': return '#ef4444';
            default: return '#94a3b8';
        }
    };

    return (
        <div className="research-progress">
            {/* Progress Bar */}
            <div style={{ marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 600 }}>Research Progress</span>
                    <span style={{ color: getStatusColor(status) }}>
                        {status.charAt(0).toUpperCase() + status.slice(1)}
                    </span>
                </div>
                <div
                    style={{
                        height: '8px',
                        background: '#e2e8f0',
                        borderRadius: '4px',
                        overflow: 'hidden',
                    }}
                >
                    <div
                        style={{
                            height: '100%',
                            width: `${currentProgress * 100}%`,
                            background: `linear-gradient(90deg, #6366f1, ${getStatusColor(status)})`,
                            borderRadius: '4px',
                            transition: 'width 0.3s ease',
                        }}
                    />
                </div>
                <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                    {Math.round(currentProgress * 100)}% complete
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div
                    style={{
                        padding: '12px',
                        background: '#fef2f2',
                        border: '1px solid #fecaca',
                        borderRadius: '6px',
                        color: '#dc2626',
                        marginBottom: '16px',
                    }}
                >
                    {error}
                </div>
            )}

            {/* Steps Log */}
            <div
                ref={containerRef}
                style={{
                    maxHeight: '300px',
                    overflow: 'auto',
                    background: '#1e293b',
                    borderRadius: '8px',
                    padding: '12px',
                    fontFamily: 'monospace',
                    fontSize: '12px',
                }}
            >
                {steps.map((step, index) => (
                    <div
                        key={index}
                        style={{
                            display: 'flex',
                            gap: '12px',
                            marginBottom: '8px',
                            color: '#e2e8f0',
                        }}
                    >
                        <span style={{ color: '#64748b', flexShrink: 0 }}>
                            {step.timestamp.toLocaleTimeString()}
                        </span>
                        <span style={{ color: getStatusColor(step.status), flexShrink: 0 }}>
                            [{step.status.toUpperCase()}]
                        </span>
                        <span>{step.message}</span>
                        {step.sources_found > 0 && (
                            <span style={{ color: '#10b981' }}>
                                ({step.sources_found} sources)
                            </span>
                        )}
                    </div>
                ))}

                {steps.length === 0 && status === 'connecting' && (
                    <div style={{ color: '#64748b' }}>Connecting to research stream...</div>
                )}
            </div>

            {/* Summary Stats */}
            {steps.length > 0 && (
                <div
                    style={{
                        marginTop: '16px',
                        display: 'flex',
                        gap: '24px',
                        fontSize: '14px',
                    }}
                >
                    <div>
                        <span style={{ color: '#64748b' }}>Steps: </span>
                        <span style={{ fontWeight: 600 }}>{steps.length}</span>
                    </div>
                    <div>
                        <span style={{ color: '#64748b' }}>Sources: </span>
                        <span style={{ fontWeight: 600 }}>
                            {steps[steps.length - 1]?.sources_found || 0}
                        </span>
                    </div>
                    <div>
                        <span style={{ color: '#64748b' }}>Duration: </span>
                        <span style={{ fontWeight: 600 }}>
                            {steps.length > 0
                                ? Math.round(
                                    (steps[steps.length - 1].timestamp.getTime() -
                                        steps[0].timestamp.getTime()) /
                                    1000
                                )
                                : 0}
                            s
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ResearchProgress;
