import React, { useState } from 'react';
import { ChevronDown, Zap, Database, ShieldCheck, Code2, Search, Globe, Brain, Cpu } from 'lucide-react';

/**
 * Cognitive Tier - Maps to System 1 (Fast) vs System 2 (Heavy Lifting)
 */
type CognitiveTier = 'SYSTEM_1' | 'SYSTEM_2';

/**
 * Step Type - Determines icon and context
 */
type StepType = 'ROUTING' | 'RETRIEVAL' | 'SECURITY' | 'EXECUTION' | 'GRAPH' | 'WEB' | 'CODE';

/**
 * Thought Step - Single reasoning step in the accordion
 */
interface ThoughtStep {
    id: string;
    step: string;
    content: string;
    type: StepType;
    tier: CognitiveTier;
    timestamp?: number;
    metadata?: Record<string, any>;
}

interface ThoughtAccordionProps {
    steps: ThoughtStep[];
    isThinking?: boolean;
    defaultExpanded?: boolean;
}

/**
 * Returns the appropriate icon component for a step type
 */
const StepIcon: React.FC<{ type: StepType; tier: CognitiveTier }> = ({ type, tier }) => {
    // Use tier-based coloring: System 1 = Emerald (Fast), System 2 = Violet (Heavy)
    const tierColor = tier === 'SYSTEM_1' ? 'text-os-fast' : 'text-os-heavy';

    switch (type) {
        case 'ROUTING':
            return <Zap className={`w-4 h-4 ${tierColor}`} />;
        case 'RETRIEVAL':
            return <Database className={`w-4 h-4 ${tierColor}`} />;
        case 'SECURITY':
            return <ShieldCheck className={`w-4 h-4 ${tierColor}`} />;
        case 'EXECUTION':
            return <Cpu className={`w-4 h-4 ${tierColor}`} />;
        case 'GRAPH':
            return <Brain className={`w-4 h-4 ${tierColor}`} />;
        case 'WEB':
            return <Globe className={`w-4 h-4 ${tierColor}`} />;
        case 'CODE':
            return <Code2 className={`w-4 h-4 ${tierColor}`} />;
        default:
            return <Search className={`w-4 h-4 ${tierColor}`} />;
    }
};

/**
 * Tier Badge - Shows System 1 or System 2 indicator
 */
const TierBadge: React.FC<{ tier: CognitiveTier }> = ({ tier }) => {
    const isSystem1 = tier === 'SYSTEM_1';
    return (
        <span
            className={`
                text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider
                ${isSystem1
                    ? 'text-os-fast bg-os-fast/10 border border-os-fast/20'
                    : 'text-os-heavy bg-os-heavy/10 border border-os-heavy/20'}
            `}
        >
            {isSystem1 ? 'Fast Lane' : 'Deep Reasoning'}
        </span>
    );
};

/**
 * Single step item in the accordion
 */
const StepItem: React.FC<{ step: ThoughtStep; index: number }> = ({ step, index }) => {
    return (
        <div
            className="flex gap-3 items-start animate-in fade-in slide-in-from-left-2 duration-300"
            style={{ animationDelay: `${index * 50}ms` }}
        >
            {/* Icon Container */}
            <div className="mt-1 p-1.5 rounded-lg bg-os-surface border border-os-border">
                <StepIcon type={step.type} tier={step.tier} />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                        {step.step}
                    </p>
                    <TierBadge tier={step.tier} />
                </div>
                <p className="text-sm text-slate-300 leading-relaxed">
                    {step.content}
                </p>
                {step.metadata && (
                    <div className="mt-1 text-[10px] text-slate-500 font-mono">
                        {JSON.stringify(step.metadata)}
                    </div>
                )}
            </div>
        </div>
    );
};

/**
 * Thinking Pulse Animation
 */
const ThinkingPulse: React.FC = () => (
    <div className="flex items-center gap-2 p-3">
        <div className="flex gap-1">
            <div className="w-2 h-2 rounded-full bg-os-heavy animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-2 h-2 rounded-full bg-os-heavy animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-2 h-2 rounded-full bg-os-heavy animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
        <span className="text-xs text-slate-400 italic">Processing...</span>
    </div>
);

/**
 * ThoughtAccordion - Main component for visualizing the cognitive router's reasoning process
 * 
 * This component displays the "Glass Box" view of how PandoraLM processes queries,
 * distinguishing between:
 * - System 1 (Fast Lane): Semantic routing, simple vector retrieval
 * - System 2 (Deep Reasoning): GraphRAG, multi-step inference, web research
 */
export const ThoughtAccordion: React.FC<ThoughtAccordionProps> = ({
    steps,
    isThinking = false,
    defaultExpanded = true,
}) => {
    const [isOpen, setIsOpen] = useState(defaultExpanded);

    if (!steps || steps.length === 0) {
        if (isThinking) {
            return (
                <div className="mb-4 rounded-xl border border-os-border bg-os-surface/30 backdrop-blur-os overflow-hidden">
                    <ThinkingPulse />
                </div>
            );
        }
        return null;
    }

    // Get unique tiers present in the steps
    const presentTiers = [...new Set(steps.map(s => s.tier))];
    const presentTypes = [...new Set(steps.map(s => s.type))];

    return (
        <div className="mb-4 rounded-xl border border-os-border bg-os-surface/30 backdrop-blur-os overflow-hidden transition-all">
            {/* Header */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between p-3 hover:bg-os-surface/50 transition-colors"
            >
                <div className="flex items-center gap-2">
                    {/* Tier Icons Stack */}
                    <div className="flex -space-x-2">
                        {presentTypes.slice(0, 3).map((type, idx) => (
                            <div
                                key={type}
                                className="p-1.5 rounded-full bg-os-bg border border-os-border z-10"
                                style={{ zIndex: 10 - idx }}
                            >
                                <StepIcon type={type} tier={presentTiers[0] || 'SYSTEM_1'} />
                            </div>
                        ))}
                    </div>

                    {/* Title */}
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-2">
                        Reasoning Trace
                    </span>

                    {/* Tier Indicators */}
                    <div className="flex gap-1 ml-2">
                        {presentTiers.includes('SYSTEM_1') && (
                            <div className="w-2 h-2 rounded-full bg-os-fast shadow-[0_0_4px_#10B981]" />
                        )}
                        {presentTiers.includes('SYSTEM_2') && (
                            <div className="w-2 h-2 rounded-full bg-os-heavy shadow-[0_0_4px_#8B5CF6]" />
                        )}
                    </div>
                </div>

                {/* Expand/Collapse */}
                <ChevronDown
                    className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                />
            </button>

            {/* Content */}
            {isOpen && (
                <div className="p-4 pt-0 space-y-4 border-t border-os-border/50">
                    {steps.map((step, idx) => (
                        <StepItem key={step.id || idx} step={step} index={idx} />
                    ))}
                    {isThinking && <ThinkingPulse />}
                </div>
            )}
        </div>
    );
};

export default ThoughtAccordion;

// Export types for use in stream parser
export type { ThoughtStep, StepType, CognitiveTier };
