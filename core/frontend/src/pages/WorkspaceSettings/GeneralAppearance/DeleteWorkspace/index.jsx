import { useState } from "react";
import { useParams } from "react-router-dom";
import Workspace from "@/models/workspace";
import paths from "@/utils/paths";
import { useTranslation } from "react-i18next";
import showToast from "@/utils/toast";
import DeleteConfirmationModal from "@/components/Modals/DeleteConfirmationModal";

export default function DeleteWorkspace({ workspace }) {
  const { slug } = useParams();
  const [deleting, setDeleting] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const { t } = useTranslation();

  const handleDelete = async () => {
    setDeleting(true);
    const success = await Workspace.delete(workspace.slug);
    if (!success) {
      showToast("Workspace could not be deleted!", "error", { clear: true });
      setDeleting(false);
      setShowConfirmation(false);
      return;
    }

    workspace.slug === slug
      ? (window.location = "/")
      : window.location.reload();
  };

  return (
    <div className="flex flex-col mt-10">
      <label className="block input-label !text-[#252525]">
        {t("general.delete.title")}
      </label>
      <p className="text-[#545454] text-xs font-medium py-1.5 opacity-80">
        {t("general.delete.description")}
      </p>
      <button
        disabled={deleting}
        onClick={() => setShowConfirmation(true)}
        type="button"
        className="w-60 mt-4 transition-all duration-300 border border-transparent rounded-lg whitespace-nowrap text-sm px-5 py-2.5 focus:z-10 bg-red-500/25 text-red-700 light:text-red-500 hover:light:text-[#FFFFFF] hover:text-[#FFFFFF] hover:bg-red-600 disabled:bg-red-600 disabled:text-red-200 disabled:animate-pulse"
      >
        {deleting ? t("general.delete.deleting") : t("general.delete.delete")}
      </button>

      <DeleteConfirmationModal
        isOpen={showConfirmation}
        onClose={() => setShowConfirmation(false)}
        onConfirm={handleDelete}
        title={t("general.delete.title")}
        message={`${t("general.delete.confirm-start")} ${workspace.name} ${t(
          "general.delete.confirm-end"
        )}`}
        loading={deleting}
      />
    </div>
  );
}

