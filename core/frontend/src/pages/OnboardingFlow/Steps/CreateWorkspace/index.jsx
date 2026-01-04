import React, { useEffect, useState } from "react";
import { Box, ArrowLeft } from "lucide-react";
import paths from "@/utils/paths";
import showToast from "@/utils/toast";
import { useNavigate } from "react-router-dom";
import Workspace from "@/models/workspace";
import { useTranslation } from "react-i18next";

export default function CreateWorkspace({
  setHeader,
  setForwardBtn,
  setBackBtn,
}) {
  const { t } = useTranslation();
  const [workspaceName, setWorkspaceName] = useState("");
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Suppress default layout header & buttons
    setHeader({ title: "", description: "" });
    setBackBtn({ showing: false, disabled: true, onClick: () => null });
    setForwardBtn({ showing: false, disabled: true, onClick: () => null });
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!workspaceName.trim() || loading) return;
    setLoading(true);

    const { workspace, error } = await Workspace.new({
      name: workspaceName,
      onboardingComplete: true,
    });
    if (!!workspace) {
      showToast(
        "Workspace created successfully! Taking you to home...",
        "success"
      );
      await new Promise((resolve) => setTimeout(resolve, 1000));
      navigate(paths.home());
    } else {
      showToast(`Failed to create workspace: ${error}`, "error");
      setLoading(false);
    }
  };

  function handleBack() {
    navigate(paths.onboarding.survey());
  }

  return (
    <div className="bg-white shadow-2xl border border-gray-100 rounded-xl p-10 max-w-md w-full mx-auto relative z-10 flex flex-col items-center">
      {/* Header */}
      <Box className="w-12 h-12 text-[#252525] mb-4" strokeWidth={1.5} />
      <h1 className="text-[#252525] font-bold text-2xl text-center mb-2">
        Name your Workspace
      </h1>
      <p className="text-[#545454] text-sm text-center mb-8">
        This will be your private knowledge base.
      </p>

      {/* Form */}
      <form onSubmit={handleCreate} className="w-full flex flex-col gap-y-4">
        <div>
          <label htmlFor="name" className="sr-only">
            {t("common.workspaces-name")}
          </label>
          <input
            name="name"
            type="text"
            className="bg-white border-2 border-[#7D7D7D] text-[#252525] text-lg font-medium p-4 focus:outline-none focus:ring-0 focus:border-[#252525] placeholder:text-gray-400 w-full rounded-lg transition-colors"
            placeholder="e.g., Engineering Team, Project Alpha"
            required={true}
            autoComplete="off"
            value={workspaceName}
            onChange={(e) => setWorkspaceName(e.target.value)}
          />
        </div>

        {/* Continue Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-[#252525] text-white rounded-lg py-3 px-6 font-semibold hover:bg-[#333333] transition-all shadow-lg mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Creating..." : "Continue"}
        </button>
      </form>

      {/* Back Button */}
      <button
        onClick={handleBack}
        className="text-[#545454] hover:text-[#252525] flex items-center gap-2 text-sm font-medium transition-colors mt-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Go Back
      </button>
    </div>
  );
}
