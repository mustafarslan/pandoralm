import React from 'react';
import { Code2, FileCode, ExternalLink, ChevronRight } from 'lucide-react';

interface AstData {
    file: string;
    className?: string;
    methodName?: string;
    breadcrumb: string;
    language?: string;
}

interface CodeBlockCardProps {
    astData: AstData;
    onClick?: () => void;
}

/**
 * CodeBlockCard - A clickable card that triggers the Code Context view in the side panel
 * 
 * This component is rendered inline in the chat when the AI references code.
 * Clicking it opens the IntelligenceSidePanel in CODE mode.
 */
const CodeBlockCard: React.FC<CodeBlockCardProps> = ({ astData, onClick }) => {
    const breadcrumbParts = astData.breadcrumb.split(' > ').filter(Boolean);

    return (
        <div
            onClick={onClick}
            className="
                bg-ink-panel border border-ink-border rounded-xl p-3 my-2 max-w-md
                hover:border-os-code transition-all cursor-pointer group
                shadow-lg hover:shadow-[0_0_20px_rgba(59,130,246,0.15)]
            "
        >
            <div className="flex items-start gap-3">
                {/* Code Icon */}
                <div className="p-2 bg-os-code/10 text-os-code rounded-lg group-hover:bg-os-code group-hover:text-white transition-all">
                    <Code2 size={20} />
                </div>

                <div className="flex-1 min-w-0">
                    {/* File Name */}
                    <div className="flex items-center gap-2">
                        <FileCode size={14} className="text-ink-muted" />
                        <span className="text-sm font-mono text-ink-primary truncate">
                            {astData.file.split('/').pop()}
                        </span>
                        {astData.language && (
                            <span className="text-[10px] text-os-code font-mono uppercase px-1.5 py-0.5 bg-os-code/10 rounded">
                                {astData.language}
                            </span>
                        )}
                    </div>

                    {/* AST Breadcrumb */}
                    <div className="flex items-center gap-1 mt-2 text-xs text-ink-muted overflow-x-auto no-scroll">
                        {breadcrumbParts.map((part, idx) => (
                            <React.Fragment key={idx}>
                                {idx > 0 && <ChevronRight size={12} className="text-ink-muted flex-shrink-0" />}
                                <span
                                    className={`
                                        font-mono whitespace-nowrap
                                        ${idx === breadcrumbParts.length - 1
                                            ? 'text-os-code font-medium'
                                            : 'text-ink-muted'}
                                    `}
                                >
                                    {part}
                                </span>
                            </React.Fragment>
                        ))}
                    </div>

                    {/* Method/Class highlight */}
                    {(astData.className || astData.methodName) && (
                        <div className="mt-2 text-[10px] text-ink-muted">
                            {astData.className && (
                                <span className="mr-2">
                                    Class: <span className="text-os-heavy">{astData.className}</span>
                                </span>
                            )}
                            {astData.methodName && (
                                <span>
                                    Method: <span className="text-os-code">{astData.methodName}()</span>
                                </span>
                            )}
                        </div>
                    )}
                </div>

                {/* Open indicator */}
                <ExternalLink
                    size={14}
                    className="text-ink-muted group-hover:text-os-code transition-colors mt-1"
                />
            </div>
        </div>
    );
};

export default CodeBlockCard;
