import React from 'react';
import { PrismLight as SyntaxHighlighter } from 'react-syntax-highlighter';
import python from 'react-syntax-highlighter/dist/esm/languages/prism/python';
import javascript from 'react-syntax-highlighter/dist/esm/languages/prism/javascript';
import { nord } from 'react-syntax-highlighter/dist/esm/styles/prism';

SyntaxHighlighter.registerLanguage('python', python);
SyntaxHighlighter.registerLanguage('javascript', javascript);

// Custom "Ink Code" Theme
const inkTheme = {
    ...nord,
    'code[class*="language-"]': { color: '#CFCFCF', background: 'transparent' },
    'pre[class*="language-"]': { background: '#252525', margin: 0 },
    'comment': { color: '#7D7D7D', fontStyle: 'italic' },
    'keyword': { color: '#FFFFFF', fontWeight: 'bold' },
    'string': { color: '#A8A8A8' },
    'function': { color: '#FFFFFF' },
};

interface CodeViewerProps {
    data: {
        language: string;
        code: string;
        filepath: string;
        startLine?: number;
    };
}

export const CodeViewer: React.FC<CodeViewerProps> = ({ data }) => {
    return (
        <div className="flex flex-col h-full bg-[#252525] border-l border-[#545454]">
            {/* Header */}
            <div className="p-4 border-b border-[#545454] bg-[#252525] flex justify-between items-center">
                <div>
                    <h3 className="text-sm font-bold uppercase tracking-widest text-[#CFCFCF]">
                        Code Brain
                    </h3>
                    <p className="text-xs text-[#7D7D7D] font-mono mt-1 break-all">
                        {data.filepath}
                    </p>
                </div>
                <div className="bg-[#545454] px-2 py-1 rounded text-xs text-white font-mono uppercase">
                    {data.language}
                </div>
            </div>

            {/* Code Editor View */}
            <div className="flex-1 overflow-auto bg-[#252525] text-sm font-mono">
                <SyntaxHighlighter
                    language={data.language}
                    style={inkTheme}
                    showLineNumbers={true}
                    startingLineNumber={data.startLine || 1}
                    lineNumberStyle={{ color: '#545454', minWidth: '2.5em' }}
                    customStyle={{ margin: 0, padding: '1.5rem', background: 'transparent' }}
                >
                    {data.code}
                </SyntaxHighlighter>
            </div>
        </div>
    );
};
