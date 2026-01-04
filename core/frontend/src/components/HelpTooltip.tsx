import React, { useState } from 'react';
import { HelpCircle } from 'lucide-react';

interface HelpTooltipProps {
    text: string;
}

export const HelpTooltip = ({ text }: HelpTooltipProps) => {
    const [isVisible, setIsVisible] = useState(false);

    return (
        <div
            className="relative inline-block ml-2"
            onMouseEnter={() => setIsVisible(true)}
            onMouseLeave={() => setIsVisible(false)}
        >
            <button className="text-[var(--ink-meta)] hover:text-[var(--ink-heading)] transition-colors cursor-help translate-y-[2px]">
                <HelpCircle size={14} />
            </button>

            {isVisible && (
                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-48 px-3 py-2 text-xs font-medium bg-white text-[var(--ink-body)] border border-[var(--ink-border)] rounded-md shadow-lg z-50 animate-in fade-in zoom-in-95">
                    {text}
                    <div className="absolute left-1/2 -translate-x-1/2 top-full w-2 h-2 bg-white border-r border-b border-[var(--ink-border)] rotate-45 -translate-y-1"></div>
                </div>
            )}
        </div>
    );
};
