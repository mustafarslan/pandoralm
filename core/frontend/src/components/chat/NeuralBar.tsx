import React from 'react';
import { Zap, Brain, Cpu, Globe } from 'lucide-react';
import { useGlassBoxSafe } from '@/contexts/GlassBoxContext';
import type { CognitiveTier } from './ThoughtAccordion';

interface NeuralBarProps {
    className?: string;
}

/**
 * NeuralBar - Visual indicator showing which cognitive tier is currently active
 * 
 * This component provides instant feedback about the system's processing mode:
 * - Green (Emerald): System 1 - Fast, semantic routing
 * - Violet: System 2 - Deep reasoning, GraphRAG, multi-step inference
 * 
 * It pulses when actively thinking to indicate processing.
 */
export const NeuralBar: React.FC<NeuralBarProps> = ({ className = '' }) => {
    const glassBox = useGlassBoxSafe();

    if (!glassBox) return null;

    const { currentTier, isThinking } = glassBox;
    const isSystem1 = currentTier === 'SYSTEM_1';

    return (
        <div
            className={`
                flex items-center gap-2 px-3 py-1.5 rounded-full
                border transition-all duration-300
                ${isSystem1
                    ? 'bg-os-fast/10 border-os-fast/30'
                    : 'bg-os-heavy/10 border-os-heavy/30'}
                ${isThinking ? 'animate-pulse' : ''}
                ${className}
            `}
        >
            {/* Tier Icon */}
            <div
                className={`
                    w-2 h-2 rounded-full transition-all duration-300
                    ${isSystem1
                        ? 'bg-os-fast shadow-[0_0_8px_#10B981]'
                        : 'bg-os-heavy shadow-[0_0_8px_#8B5CF6]'}
                `}
            />

            {/* Mode Indicator */}
            {isSystem1 ? (
                <Zap size={14} className="text-os-fast" />
            ) : (
                <Brain size={14} className="text-os-heavy" />
            )}

            {/* Label */}
            <span
                className={`
                    text-[10px] font-bold uppercase tracking-wider
                    ${isSystem1 ? 'text-os-fast' : 'text-os-heavy'}
                `}
            >
                {isSystem1 ? 'Fast Lane' : 'Deep Reasoning'}
            </span>

            {/* Active Processing Indicator */}
            {isThinking && (
                <div className="flex gap-0.5 ml-1">
                    <div
                        className={`w-1 h-1 rounded-full animate-bounce ${isSystem1 ? 'bg-os-fast' : 'bg-os-heavy'}`}
                        style={{ animationDelay: '0ms' }}
                    />
                    <div
                        className={`w-1 h-1 rounded-full animate-bounce ${isSystem1 ? 'bg-os-fast' : 'bg-os-heavy'}`}
                        style={{ animationDelay: '150ms' }}
                    />
                    <div
                        className={`w-1 h-1 rounded-full animate-bounce ${isSystem1 ? 'bg-os-fast' : 'bg-os-heavy'}`}
                        style={{ animationDelay: '300ms' }}
                    />
                </div>
            )}
        </div>
    );
};

/**
 * Minimal version for embedding in tight spaces
 */
export const NeuralDot: React.FC<{ className?: string }> = ({ className = '' }) => {
    const glassBox = useGlassBoxSafe();

    if (!glassBox) return null;

    const { currentTier, isThinking } = glassBox;
    const isSystem1 = currentTier === 'SYSTEM_1';

    return (
        <div
            className={`
                w-3 h-3 rounded-full transition-all duration-300
                ${isSystem1
                    ? 'bg-os-fast shadow-[0_0_8px_#10B981]'
                    : 'bg-os-heavy shadow-[0_0_8px_#8B5CF6]'}
                ${isThinking ? 'animate-pulse' : ''}
                ${className}
            `}
            title={isSystem1 ? 'Fast Lane (System 1)' : 'Deep Reasoning (System 2)'}
        />
    );
};

export default NeuralBar;
