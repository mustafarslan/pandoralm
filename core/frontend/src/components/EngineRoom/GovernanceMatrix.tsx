import React, { useState, useEffect } from 'react';
import { Shield, Users, Layers, HardDrive, Lock } from 'lucide-react';
import System from '@/models/system';

interface LayerMeta {
    id: string;
    name: string;
    type: 'SYSTEM' | 'ORG' | 'TEAM' | 'USER';
    size_mb: number;
    doc_count: number;
    role_map: string[];
}

export const GovernanceMatrix = () => {
    const [layers, setLayers] = useState<LayerMeta[]>([]);

    useEffect(() => {
        const fetchLayers = async () => {
            const data = await System.listLayers(true);
            if (Array.isArray(data)) {
                const mapped = data.map((l: any) => ({
                    id: l.id,
                    name: l.name,
                    type: l.type,
                    size_mb: l.size_bytes ? l.size_bytes / (1024 * 1024) : 0,
                    doc_count: l.vector_count || 0,
                    role_map: l.permissions?.map((p: any) => p.role_pattern) || []
                }));
                setLayers(mapped);
            }
        };
        fetchLayers();
    }, []);

    return (
        <div className="bg-transparent text-[var(--ink-primary)]">

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Layer Inspector */}
                <div className="rounded-lg border border-[var(--ink-border)] bg-white shadow-[4px_4px_0px_0px_var(--ink-shadow)] p-6">
                    <div className="flex justify-between items-center mb-4">
                        <h4 className="text-sm font-bold flex items-center gap-2 text-[var(--ink-heading)]">
                            <Layers size={14} className="text-[var(--ink-primary)]" /> Active Knowledge Layers
                        </h4>
                        <span className="text-[10px] bg-[var(--ink-page)] border border-[var(--ink-border)] px-2 py-1 rounded text-[var(--ink-muted)]">
                            Total Size: {layers.reduce((acc, l) => acc + (l.size_mb || 0), 0).toFixed(1)} MB
                        </span>
                    </div>

                    <div className="space-y-2">
                        {layers.map(layer => (
                            <div key={layer.id} className="group flex items-center justify-between p-3 bg-white border border-[var(--ink-border)] rounded-md hover:shadow-sm transition-all">
                                <div className="flex items-center gap-3">
                                    <div className={`p-1.5 rounded
                                        ${layer.type === 'SYSTEM' ? 'text-blue-600 bg-blue-50' :
                                            layer.type === 'ORG' ? 'text-purple-600 bg-purple-50' :
                                                layer.type === 'TEAM' ? 'text-emerald-600 bg-emerald-50' : 'text-gray-400 bg-gray-50'
                                        }
                                    `}>
                                        <Users size={14} />
                                    </div>
                                    <div>
                                        <div className="text-sm font-medium text-[var(--ink-heading)]">{layer.name}</div>
                                        <div className="text-[10px] font-mono text-[var(--ink-muted)]">{layer.id}</div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="text-xs font-bold text-[var(--ink-primary)] flex items-center justify-end gap-1">
                                        <HardDrive size={10} className="text-[var(--ink-muted)]" /> {layer.size_mb.toFixed(2)} MB
                                    </div>
                                    <div className="text-[10px] text-[var(--ink-muted)]">{layer.doc_count} docs</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Identity Passport Mapping */}
                <div className="rounded-lg border border-[var(--ink-border)] bg-white shadow-[4px_4px_0px_0px_var(--ink-shadow)] p-6">
                    <div className="flex justify-between items-center mb-4">
                        <h4 className="text-sm font-bold flex items-center gap-2 text-[var(--ink-heading)]">
                            <Lock size={14} className="text-[var(--ink-primary)]" /> Identity Passport Mapping
                        </h4>
                        <button className="text-[10px] text-[var(--ink-primary)] hover:underline transition-colors uppercase font-bold">
                            + Add Rule
                        </button>
                    </div>

                    <div className="ink-table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th className="bg-[var(--ink-panel)] text-[var(--ink-muted)] border-b-2 border-[var(--ink-primary)]">Keycloak Role / Group</th>
                                    <th className="bg-[var(--ink-panel)] text-[var(--ink-muted)] border-b-2 border-[var(--ink-primary)]">Access Level</th>
                                    <th className="bg-[var(--ink-panel)] text-[var(--ink-muted)] border-b-2 border-[var(--ink-primary)]">Target Layer</th>
                                </tr>
                            </thead>
                            <tbody>
                                {layers.flatMap(l => l.role_map.map((role, i) => (
                                    <tr key={`${l.id}-${i}`} className="border-b border-[var(--ink-border)] hover:bg-[var(--ink-page)]">
                                        <td className="font-mono text-[var(--ink-muted)]">{role}</td>
                                        <td>
                                            <span className="ink-badge success">
                                                READ_WRITE
                                            </span>
                                        </td>
                                        <td className="text-[var(--ink-primary)]">{l.name}</td>
                                    </tr>
                                )))}
                            </tbody>
                        </table>
                    </div>
                    <div className="mt-4 p-3 rounded bg-amber-50 border border-amber-200 text-[10px] text-amber-600">
                        <p className="font-bold flex items-center gap-2 mb-1">
                            <Shield size={12} />
                            Zero-Trust Enforcement Active
                        </p>
                        All permission changes here are synced to Postgres and cached in Redis (TTL: 5m).
                        Vector search queries verify these rules at query-time via <code>IN</code> clauses.
                    </div>
                </div>

            </div>
        </div>
    );
};

export default GovernanceMatrix;
