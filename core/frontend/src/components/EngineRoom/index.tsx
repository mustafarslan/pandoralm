import React from 'react';
import { isAdmin } from '@/utils/rbac';
import WorkerHUD from './WorkerHUD';
import PipelineStats from './PipelineStats';
import GovernanceMatrix from './GovernanceMatrix';
import QuotaManager from './QuotaManager';
import { QualityGateHUD } from './QualityGateHUD';
import EngineRoomConfig from './EngineRoomConfig';
import AdminConsoleConfig from './AdminConsole';
import { HelpTooltip } from '@/components/HelpTooltip';

const EngineRoomLayout = () => {
    return (
        <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto bg-[var(--ink-bg)] scroll-smooth" id="engine-room-container">
            {/* Header - System Observability */}
            <div id="observability">
                <h1 className="text-2xl font-bold text-[var(--ink-heading)]">Settings</h1>
                <p className="text-sm text-[var(--ink-meta)]">System Observability & Configuration</p>
            </div>

            {/* Zone 1: Infrastructure Vital Signs */}
            <section>
                <WorkerHUD />
            </section>

            {/* Zone 2: Ingestion Assembly Line */}
            <section id="ingestion">
                <h3 className="text-xs font-bold text-[var(--ink-heading)] uppercase tracking-widest mb-4 flex items-center gap-2">
                    Ingestion Assembly Line
                    <HelpTooltip text="Monitors the document processing pipeline." />
                </h3>
                <PipelineStats />
            </section>

            {/* Zone 3: Governance & Identity */}
            <section id="governance">
                <h3 className="text-xs font-bold text-[var(--ink-heading)] uppercase tracking-widest mb-4 flex items-center gap-2">
                    ReBAC & Governance Matrix
                    <HelpTooltip text="Manages Role-Based Access Control policies and identity verification layers." />
                </h3>
                <GovernanceMatrix />
            </section>

            {/* Zone 3.5: Quota Management */}
            {isAdmin() && (
                <section id="quotas">
                    <h3 className="text-xs font-bold text-[var(--ink-heading)] uppercase tracking-widest mb-4 flex items-center gap-2">
                        Storage Quota Management
                        <HelpTooltip text="Manage storage limits and tiers for all knowledge layers." />
                    </h3>
                    <QuotaManager />
                </section>
            )}

            {/* Zone 4: Quality Gate HUD */}
            <section id="quality">
                <h3 className="text-xs font-bold text-[var(--ink-heading)] uppercase tracking-widest mb-4 flex items-center gap-2">
                    Gold Standard Verification Queue
                    <HelpTooltip text="Queue for human verification of AI responses to maintain high quality standards." />
                </h3>
                <QualityGateHUD />
            </section>

            {/* Zone 5: System Configuration */}
            <section id="configuration">
                <h3 className="text-xs font-bold text-[var(--ink-heading)] uppercase tracking-widest mb-4 flex items-center gap-2">
                    System Configuration
                </h3>
                <EngineRoomConfig />
            </section>

            {/* Zone 6: Admin Console (Hybrid Ops) - Protected */}
            {isAdmin() && (
                <section id="admin" className="mt-4">
                    <h3 className="text-xs font-bold text-[var(--ink-heading)] uppercase tracking-widest mb-4 flex items-center gap-2">
                        Admin Console (Hybrid Ops)
                    </h3>
                    <AdminConsoleConfig />
                </section>
            )}
        </div>
    );
};

export default EngineRoomLayout;
