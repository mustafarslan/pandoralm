import React, { useState, useEffect } from 'react';
import System from '@/models/system';
import { HardDrive, Save, Edit2, Users, Layers, AlertCircle } from 'lucide-react';
import { toast } from 'react-toastify';

export const QuotaManager = () => {
    const [layers, setLayers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editForm, setEditForm] = useState<{ quota_tier: string, storage_quota_bytes: number }>({
        quota_tier: 'FREE',
        storage_quota_bytes: 104857600
    });

    // Bulk Update State
    const [bulkType, setBulkType] = useState('USER');
    const [bulkTier, setBulkTier] = useState('FREE');

    useEffect(() => {
        fetchLayers();
    }, []);

    const fetchLayers = async () => {
        setLoading(true);
        const data = await System.listLayers(true);
        if (Array.isArray(data)) {
            setLayers(data);
        }
        setLoading(false);
    };

    const handleEdit = (layer: any) => {
        setEditingId(layer.id);
        setEditForm({
            quota_tier: layer.quota_tier || 'FREE',
            storage_quota_bytes: layer.storage_quota_bytes || 104857600
        });
    };

    const handleSave = async (layerId: string) => {
        const res = await System.updateLayerQuota(layerId, editForm);
        if (res?.success !== false) {
            toast.success("Layer quota updated");
            setEditingId(null);
            fetchLayers();
        } else {
            toast.error(res.error || "Failed to update quota");
        }
    };

    const handleBulkUpdate = async () => {
        if (!window.confirm(`Are you sure you want to update ALL ${bulkType} layers to ${bulkTier}? This cannot be undone.`)) return;

        const res = await System.bulkUpdateQuotas({
            target_type: bulkType,
            quota_tier: bulkTier
        });

        if (res?.success !== false) {
            toast.success(`Updated ${res.updated_count} layers.`);
            fetchLayers();
        } else {
            toast.error(res.error || "Failed to bulk update");
        }
    }

    const formatBytes = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    return (
        <div className="space-y-6">
            {/* Bulk Actions */}
            <div className="bg-white p-4 rounded-lg border border-[var(--ink-border)] shadow-sm">
                <h4 className="text-sm font-bold text-[var(--ink-heading)] mb-3 flex items-center gap-2">
                    <Layers size={14} /> Bulk Quota Policy
                </h4>
                <div className="flex items-end gap-4">
                    <div>
                        <label className="text-xs font-bold text-[var(--ink-muted)] block mb-1">Target Layer Type</label>
                        <select
                            className="text-sm border border-[var(--ink-border)] rounded px-2 py-1 bg-[var(--ink-bg)]"
                            value={bulkType}
                            onChange={(e) => setBulkType(e.target.value)}
                        >
                            <option value="USER">User Private Layers</option>
                            <option value="TEAM">Team Layers</option>
                            <option value="ORG">Organization Layers</option>
                        </select>
                    </div>
                    <div>
                        <label className="text-xs font-bold text-[var(--ink-muted)] block mb-1">Set Tier To</label>
                        <select
                            className="text-sm border border-[var(--ink-border)] rounded px-2 py-1 bg-[var(--ink-bg)]"
                            value={bulkTier}
                            onChange={(e) => setBulkTier(e.target.value)}
                        >
                            <option value="FREE">FREE (100MB)</option>
                            <option value="PRO">PRO (10GB)</option>
                            <option value="ENTERPRISE">ENTERPRISE (1TB)</option>
                        </select>
                    </div>
                    <button
                        onClick={handleBulkUpdate}
                        className="bg-[var(--ink-primary)] text-white px-3 py-1.5 rounded text-xs font-bold hover:bg-black transition-colors"
                    >
                        Apply Policy
                    </button>
                </div>
            </div>

            {/* Layer List */}
            <div className="bg-white rounded-lg border border-[var(--ink-border)] shadow-sm overflow-hidden">
                <table className="w-full text-sm text-left">
                    <thead className="bg-[var(--ink-bg)] text-[var(--ink-muted)] font-bold border-b border-[var(--ink-border)]">
                        <tr>
                            <th className="p-3">Layer Name</th>
                            <th className="p-3">Type</th>
                            <th className="p-3">Current Usage</th>
                            <th className="p-3">Quota Tier</th>
                            <th className="p-3 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--ink-border)]">
                        {loading ? (
                            <tr><td colSpan={5} className="p-4 text-center">Loading layers...</td></tr>
                        ) : layers.map(layer => (
                            <tr key={layer.id} className="hover:bg-[var(--ink-bg)]">
                                <td className="p-3 font-medium text-[var(--ink-heading)]">
                                    {layer.name}
                                    <div className="text-[10px] text-[var(--ink-muted)] font-mono">{layer.id}</div>
                                </td>
                                <td className="p-3">
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${layer.type === 'USER' ? 'bg-amber-100 text-amber-500' :
                                            layer.type === 'SYSTEM' ? 'bg-blue-100 text-blue-500' : 'bg-green-100 text-green-500'
                                        }`}>
                                        {layer.type}
                                    </span>
                                </td>
                                <td className="p-3 font-mono">
                                    {formatBytes(layer.storage_used_bytes || 0)} / {formatBytes(layer.storage_quota_bytes || 104857600)}
                                </td>
                                <td className="p-3">
                                    {layer.id === editingId ? (
                                        <select
                                            value={editForm.quota_tier}
                                            onChange={(e) => setEditForm({ ...editForm, quota_tier: e.target.value })}
                                            className="border rounded px-1 py-0.5"
                                        >
                                            <option value="FREE">FREE</option>
                                            <option value="PRO">PRO</option>
                                            <option value="ENTERPRISE">ENTERPRISE</option>
                                        </select>
                                    ) : (
                                        <span className="font-bold text-[var(--ink-primary)]">{layer.quota_tier || 'FREE'}</span>
                                    )}
                                </td>
                                <td className="p-3 text-right">
                                    {layer.id === editingId ? (
                                        <div className="flex justify-end gap-2">
                                            <button onClick={() => handleSave(layer.id)} className="text-green-600 hover:text-green-800"><Save size={16} /></button>
                                            <button onClick={() => setEditingId(null)} className="text-red-500 hover:text-red-700">Cancel</button>
                                        </div>
                                    ) : (
                                        <button onClick={() => handleEdit(layer)} className="text-[var(--ink-muted)] hover:text-[var(--ink-primary)]">
                                            <Edit2 size={16} />
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default QuotaManager;
