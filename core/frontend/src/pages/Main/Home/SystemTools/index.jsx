import { useNavigate } from "react-router-dom";
import paths from "@/utils/paths";
import Workspace from "@/models/workspace";
import { useTranslation } from "react-i18next";
import { Cpu, Terminal, Command } from "@phosphor-icons/react";

export default function SystemTools() {
    const { t } = useTranslation();
    const navigate = useNavigate();

    const tools = [
        {
            icon: <Cpu size={24} className="text-ink-heading" />,
            title: t("main-page.exploreMore.features.customAgents.title"),
            desc: "Autonomously execute tasks",
            action: async () => {
                const workspaces = await Workspace.all();
                if (workspaces.length > 0) {
                    navigate(paths.workspace.chat(workspaces[0].slug, { search: { action: "set-agent-chat" } }));
                }
            }
        },
        {
            icon: <Terminal size={24} className="text-ink-heading" />,
            title: t("main-page.exploreMore.features.slashCommands.title"),
            desc: "Custom /commands for speed",
            action: async () => {
                const workspaces = await Workspace.all();
                if (workspaces.length > 0) {
                    navigate(paths.workspace.chat(workspaces[0].slug, { search: { action: "open-new-slash-command-modal" } }));
                }
            }
        },
        {
            icon: <Command size={24} className="text-ink-heading" />,
            title: t("main-page.exploreMore.features.systemPrompts.title"),
            desc: "Define global behaviors",
            action: async () => {
                const workspaces = await Workspace.all();
                if (workspaces.length > 0) {
                    navigate(paths.workspace.settings.chatSettings(workspaces[0].slug, { search: { action: "focus-system-prompt" } }));
                }
            }
        }
    ];

    return (
        <div className="w-full">
            <h1 className="text-ink-muted uppercase text-xs font-bold tracking-widest mb-3 flex items-center gap-2">
                System Tools
            </h1>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {tools.map((tool, idx) => (
                    <div
                        key={idx}
                        onClick={tool.action}
                        className="group cursor-pointer bg-white border border-ink-border/10 shadow-sm hover:shadow-md rounded-xl p-6 transition-all duration-200"
                    >
                        <div className="flex items-start gap-4">
                            <div className="p-2 rounded-md bg-ink-page border border-ink-border/10 group-hover:scale-105 transition-transform text-ink-heading">
                                {tool.icon}
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-ink-heading mb-1">{tool.title}</h3>
                                <p className="text-sm text-ink-muted leading-relaxed">{tool.desc}</p>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
