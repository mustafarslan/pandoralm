import React, { useState } from 'react';
import { Trash2, AlertTriangle, FileText, Loader2 } from 'lucide-react';
import { cortexDelete } from '@/utils/cortexApi';
import showToast from '@/utils/toast';

export default function DocumentManager() {
    const [docId, setDocId] = useState('');
    const [loading, setLoading] = useState(false);
    const [confirming, setConfirming] = useState(false);
    const [workspaceId] = useState('default'); // TODO: Get from context

    const handleDelete = async () => {
        setLoading(true);
        try {
            await cortexDelete(`/api/v1/ops/vectors/document/${docId}`, { workspace_id: workspaceId });
            showToast('Document vectors deleted', 'success');
            setDocId('');
            setConfirming(false);
        } catch (e) {
            console.error(e);
            showToast('Failed to delete document', 'error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-4 space-y-6">
            <div>
                <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Context Management</h3>
                <p className="text-sm text-[var(--ink-meta)]">
                    Remove documents and their associated vector chunks from the database. This action is irreversible.
                </p>
            </div>

            <div className="p-4 bg-red-50 border border-red-100 rounded-xl">
                <div className="flex gap-3">
                    <div className="p-2 bg-red-100 rounded-lg h-fit text-red-600">
                        <AlertTriangle size={20} />
                    </div>
                    <div className="space-y-4 flex-1">
                        <div>
                            <h4 className="text-sm font-bold text-red-900">Danger Zone</h4>
                            <p className="text-xs text-red-700 mt-1 leading-relaxed">
                                Deleting a document will immediately remove all its vector embeddings from LanceDB.
                                Any active GraphRAG nodes associated solely with this document will also be orphaned or deleted.
                            </p>
                        </div>

                        <div className="w-full h-px bg-red-200/50" />

                        <div className="space-y-3">
                            <label className="block text-xs font-bold text-red-800 uppercase tracking-wider">
                                Document ID to Nullify
                            </label>
                            <div className="flex gap-2">
                                <input
                                    type="text"
                                    value={docId}
                                    onChange={(e) => {
                                        setDocId(e.target.value);
                                        setConfirming(false);
                                    }}
                                    placeholder="e.g. doc-uuid-1234"
                                    className="flex-1 px-3 py-2 rounded-lg border border-red-200 bg-white text-sm text-red-900 placeholder:text-red-300 focus:outline-none focus:ring-2 focus:ring-red-500/20"
                                />
                                {!confirming ? (
                                    <button
                                        onClick={() => setConfirming(true)}
                                        disabled={!docId}
                                        className="px-4 py-2 bg-red-100 text-red-700 font-medium rounded-lg hover:bg-red-200 disabled:opacity-50 transition-colors"
                                    >
                                        Delete
                                    </button>
                                ) : (
                                    <div className="flex gap-2 animate-in fade-in slide-in-from-right-2">
                                        <button
                                            onClick={handleDelete}
                                            disabled={loading}
                                            className="px-4 py-2 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors flex items-center gap-2"
                                        >
                                            {loading && <Loader2 size={14} className="animate-spin" />}
                                            Confirm
                                        </button>
                                        <button
                                            onClick={() => setConfirming(false)}
                                            className="px-4 py-2 bg-transparent text-red-600 font-medium rounded-lg hover:bg-red-100 transition-colors"
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
