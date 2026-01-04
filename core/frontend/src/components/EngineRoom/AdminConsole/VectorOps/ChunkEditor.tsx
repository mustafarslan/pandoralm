import React, { useState } from 'react';
import { Edit3, Save, Loader2, RefreshCw } from 'lucide-react';
import { cortexPatch } from '@/utils/cortexApi';
import showToast from '@/utils/toast';

export default function ChunkEditor() {
    const [activeChunkId, setActiveChunkId] = useState('');
    const [content, setContent] = useState('');
    const [loading, setLoading] = useState(false);
    const [searching, setSearching] = useState(false);

    // Mock function to find a chunk
    const handleSearch = async () => {
        if (!activeChunkId) return;
        setSearching(true);
        try {
            // In real implementation, this would fetch the chunk details
            await new Promise(r => setTimeout(r, 600));
            setContent(`Sample content for chunk ${activeChunkId}.\n\nThis text contains OCR errors that need to be fixed manually. Editing this text will trigger a re-embedding process using the configured model.`);
            showToast('Chunk loaded', 'success');
        } catch (e) {
            showToast('Chunk not found', 'error');
        } finally {
            setSearching(false);
        }
    };

    const handleSave = async () => {
        setLoading(true);
        try {
            await cortexPatch(`/api/v1/ops/vectors/chunk/${activeChunkId}`, { content });
            showToast('Chunk updated and re-embedded', 'success');
        } catch (e) {
            console.error(e);
            showToast('Failed to update chunk', 'error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-4 space-y-4">
            <div>
                <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Surgical Editing</h3>
                <p className="text-sm text-[var(--ink-meta)]">
                    Manually edit chunk text to fix OCR errors. Updates will trigger immediate re-embedding.
                </p>
            </div>

            <div className="flex gap-2 items-end max-w-md">
                <div className="flex-1">
                    <label className="block text-xs font-bold text-[var(--ink-meta)] uppercase tracking-wider mb-1">
                        Chunk ID
                    </label>
                    <input
                        type="text"
                        value={activeChunkId}
                        onChange={(e) => setActiveChunkId(e.target.value)}
                        placeholder="e.g. chunk_123_456"
                        className="w-full px-3 py-2 rounded-lg border border-[var(--ink-border)] bg-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-black/5"
                    />
                </div>
                <button
                    onClick={handleSearch}
                    disabled={searching || !activeChunkId}
                    className="px-4 py-2 bg-[var(--ink-heading)] text-white rounded-lg font-medium hover:bg-black/80 disabled:opacity-50 transition-colors flex items-center gap-2"
                >
                    {searching ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                    Load
                </button>
            </div>

            {content && (
                <div className="mt-6 space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <div>
                        <label className="block text-xs font-bold text-[var(--ink-meta)] uppercase tracking-wider mb-1 flex justify-between">
                            <span>Chunk Content</span>
                            <span className="font-normal normal-case opacity-70">Editing will invalidate current vector</span>
                        </label>
                        <textarea
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            rows={10}
                            className="w-full p-4 rounded-lg border border-[var(--ink-border)] bg-white text-[var(--ink-body)] leading-relaxed focus:outline-none focus:ring-2 focus:ring-black/5 resize-none"
                        />
                    </div>

                    <div className="flex justify-end pt-2">
                        <button
                            onClick={handleSave}
                            disabled={loading}
                            className="flex items-center gap-2 px-6 py-2 bg-[var(--ink-heading)] text-white rounded-lg font-medium hover:bg-black/80 disabled:opacity-50 transition-colors shadow-sm"
                        >
                            {loading ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                            Save & Re-Embed
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
