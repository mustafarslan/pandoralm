import React from 'react';
import { useGlassBoxSafe } from '@/contexts/GlassBoxContext';
import { Code2, Folder, FileCode, ChevronRight, Box } from 'lucide-react';

export const CodeContextView: React.FC = () => {
    const glassBox = useGlassBoxSafe();
    const data = glassBox?.pendingCodeBlock?.astData;

    if (!data) return null;

    const breadcrumbParts = data.breadcrumb.split(' > ').filter(Boolean);
    const fileName = data.file.split('/').pop();
    const dirPath = data.file.split('/').slice(0, -1).join('/');

    return (
        <div className="w-full h-full bg-os-bg p-6 overflow-y-auto">
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center gap-2 text-slate-400 text-xs mb-2 font-mono">
                    <Folder size={14} />
                    <span>{dirPath || 'root'}</span>
                </div>
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-os-code/20 text-os-code rounded-lg">
                        <FileCode size={24} />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-white font-mono">{fileName}</h2>
                        <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                            <span className="bg-os-code/10 text-os-code px-1.5 py-0.5 rounded font-mono uppercase">
                                Python
                            </span>
                            <span>•</span>
                            <span>AST Context Analysis</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Context Hierarchy */}
            <div className="space-y-4">
                <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">
                    Symbol Hierarchy
                </div>

                <div className="relative pl-4 border-l border-os-border space-y-6">
                    {/* Render breadcrumb as a tree */}
                    {breadcrumbParts.map((part, idx) => {
                        const isLast = idx === breadcrumbParts.length - 1;
                        const isClass = part.startsWith('Class:');
                        const isMethod = part.startsWith('Method:');
                        const label = part.replace(/^(Class|Method|File):\s*/, '');

                        return (
                            <div key={idx} className="relative group">
                                {/* Connector Dot */}
                                <div className={`
                                    absolute -left-[21px] top-3 w-2.5 h-2.5 rounded-full border-2 
                                    ${isLast ? 'bg-os-code border-os-code shadow-[0_0_8px_#3B82F6]' : 'bg-os-bg border-slate-600'}
                                    transition-all group-hover:border-os-code
                                `} />

                                <div className={`
                                    p-3 rounded-lg border transition-all
                                    ${isLast
                                        ? 'bg-os-code/10 border-os-code/30'
                                        : 'bg-os-surface border-os-border group-hover:border-os-code/50'}
                                `}>
                                    <div className="flex items-center gap-2 mb-1">
                                        {isClass ? <Box size={14} className="text-os-heavy" /> :
                                            isMethod ? <Code2 size={14} className="text-os-fast" /> :
                                                <FileCode size={14} className="text-slate-400" />}

                                        <span className={`text-[10px] font-bold uppercase tracking-wider
                                            ${isClass ? 'text-os-heavy' : isMethod ? 'text-os-fast' : 'text-slate-500'}
                                        `}>
                                            {isClass ? 'Class' : isMethod ? 'Method' : 'Module'}
                                        </span>
                                    </div>
                                    <div className={`font-mono ${isLast ? 'text-white font-bold' : 'text-slate-300'}`}>
                                        {label}
                                    </div>

                                    {isLast && (
                                        <div className="mt-3 pt-3 border-t border-os-code/20 text-xs text-slate-400 leading-relaxed font-mono">
                                            {/* Logic to show snippet preview could go here */}
                                            <div className="opacity-50">Context focused on this symbol.</div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default CodeContextView;
