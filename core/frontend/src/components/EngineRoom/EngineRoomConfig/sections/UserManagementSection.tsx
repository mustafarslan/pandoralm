import React, { useState, useEffect } from 'react';
import { Users, Mail, FolderOpen, MessageSquare, Loader2, Plus, Trash2 } from 'lucide-react';
import Admin from '@/models/admin';
import showToast from '@/utils/toast';

type SubTab = 'users' | 'invites' | 'workspaces' | 'chats';

export default function UserManagementSection() {
    const [activeSubTab, setActiveSubTab] = useState<SubTab>('users');

    const subTabs = [
        { id: 'users', label: 'Users', icon: <Users size={16} /> },
        { id: 'invites', label: 'Invitations', icon: <Mail size={16} /> },
        { id: 'workspaces', label: 'Workspaces', icon: <FolderOpen size={16} /> },
        { id: 'chats', label: 'Chat History', icon: <MessageSquare size={16} /> },
    ];

    return (
        <div className="space-y-6">
            <div className="flex gap-2 flex-wrap">
                {subTabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveSubTab(tab.id as SubTab)}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${activeSubTab === tab.id
                            ? 'bg-ink-action text-white shadow-sm'
                            : 'text-ink-muted hover:bg-ink-panel hover:text-ink-primary'
                            }`}
                    >
                        {tab.icon}
                        {tab.label}
                    </button>
                ))}
            </div>

            <div className="bg-[var(--ink-page)] rounded-lg border border-[var(--ink-border)] p-4">
                {activeSubTab === 'users' && <UsersPanel />}
                {activeSubTab === 'invites' && <InvitesPanel />}
                {activeSubTab === 'workspaces' && <WorkspacesPanel />}
                {activeSubTab === 'chats' && <ChatsPanel />}
            </div>
        </div>
    );
}

function UsersPanel() {
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchUsers() {
            try {
                const data = await Admin.users();
                setUsers(data || []);
            } catch (e) {
                console.error('Failed to fetch users:', e);
            } finally {
                setLoading(false);
            }
        }
        fetchUsers();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-[var(--ink-meta)]" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Registered Users</h3>
                <button className="flex items-center gap-1 px-3 py-1.5 bg-emerald-500 text-white rounded-lg text-sm font-medium hover:bg-emerald-600 transition-colors">
                    <Plus size={14} />
                    Add User
                </button>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-[var(--ink-border)]">
                            <th className="text-left py-2 px-3 font-medium text-[var(--ink-meta)]">Username</th>
                            <th className="text-left py-2 px-3 font-medium text-[var(--ink-meta)]">Role</th>
                            <th className="text-left py-2 px-3 font-medium text-[var(--ink-meta)]">Status</th>
                            <th className="text-right py-2 px-3 font-medium text-[var(--ink-meta)]">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map((user) => (
                            <tr key={user.id} className="border-b border-[var(--ink-border)]">
                                <td className="py-2 px-3 text-[var(--ink-body)]">{user.username}</td>
                                <td className="py-2 px-3">
                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${user.role === 'admin' ? 'bg-violet-100 text-violet-700' : 'bg-slate-100 text-slate-700'
                                        }`}>
                                        {user.role}
                                    </span>
                                </td>
                                <td className="py-2 px-3">
                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${user.suspended ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'
                                        }`}>
                                        {user.suspended ? 'Suspended' : 'Active'}
                                    </span>
                                </td>
                                <td className="py-2 px-3 text-right">
                                    <button className="text-red-500 hover:text-red-700">
                                        <Trash2 size={14} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {users.length === 0 && (
                            <tr>
                                <td colSpan={4} className="py-8 text-center text-[var(--ink-meta)]">
                                    No users found. Enable multi-user mode to manage users.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function InvitesPanel() {
    const [invites, setInvites] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchInvites() {
            try {
                const data = await Admin.invites();
                setInvites(data || []);
            } catch (e) {
                console.error('Failed to fetch invites:', e);
            } finally {
                setLoading(false);
            }
        }
        fetchInvites();
    }, []);

    const handleCreateInvite = async () => {
        try {
            const { invite, error } = await Admin.newInvite({});
            if (error) {
                showToast(`Error: ${error}`, 'error');
            } else {
                showToast('Invite created!', 'success');
                setInvites([...invites, invite]);
            }
        } catch (e) {
            showToast('Failed to create invite', 'error');
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-[var(--ink-meta)]" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Invitation Codes</h3>
                <button
                    onClick={handleCreateInvite}
                    className="flex items-center gap-1 px-3 py-1.5 bg-emerald-500 text-white rounded-lg text-sm font-medium hover:bg-emerald-600 transition-colors"
                >
                    <Plus size={14} />
                    Create Invite
                </button>
            </div>

            <div className="space-y-2">
                {invites.map((invite) => (
                    <div key={invite.id} className="flex items-center justify-between p-3 bg-white rounded-lg border border-[var(--ink-border)]">
                        <div>
                            <code className="text-sm font-mono text-[var(--ink-body)]">{invite.code}</code>
                            <p className="text-xs text-[var(--ink-meta)] mt-1">
                                Status: {invite.status} {invite.claimedBy && `• Claimed by ${invite.claimedBy}`}
                            </p>
                        </div>
                        <button className="text-red-500 hover:text-red-700">
                            <Trash2 size={14} />
                        </button>
                    </div>
                ))}
                {invites.length === 0 && (
                    <p className="py-8 text-center text-[var(--ink-meta)]">
                        No invitations created yet.
                    </p>
                )}
            </div>
        </div>
    );
}

function WorkspacesPanel() {
    const [workspaces, setWorkspaces] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchWorkspaces() {
            try {
                const data = await Admin.workspaces();
                setWorkspaces(data || []);
            } catch (e) {
                console.error('Failed to fetch workspaces:', e);
            } finally {
                setLoading(false);
            }
        }
        fetchWorkspaces();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-[var(--ink-meta)]" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">All Workspaces</h3>

            <div className="grid gap-3">
                {workspaces.map((ws) => (
                    <div key={ws.id} className="flex items-center justify-between p-3 bg-white rounded-lg border border-[var(--ink-border)]">
                        <div>
                            <p className="text-sm font-medium text-[var(--ink-body)]">{ws.name}</p>
                            <p className="text-xs text-[var(--ink-meta)]">Slug: {ws.slug}</p>
                        </div>
                    </div>
                ))}
                {workspaces.length === 0 && (
                    <p className="py-8 text-center text-[var(--ink-meta)]">
                        No workspaces found.
                    </p>
                )}
            </div>
        </div>
    );
}

function ChatsPanel() {
    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--ink-heading)]">Chat History</h3>
            <p className="text-sm text-[var(--ink-meta)]">
                View and manage chat history across all workspaces.
            </p>
            <div className="py-8 text-center text-[var(--ink-meta)] border border-dashed border-[var(--ink-border)] rounded-lg">
                Chat history viewer coming soon...
            </div>
        </div>
    );
}
