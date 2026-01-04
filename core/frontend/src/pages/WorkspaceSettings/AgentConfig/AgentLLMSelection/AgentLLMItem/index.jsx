// This component differs from the main LLMItem in that it shows if a provider is
// "ready for use" and if not - will then highjack the click handler to show a modal
// of the provider options that must be saved to continue.
import { createPortal } from "react-dom";
import ModalWrapper from "@/components/ModalWrapper";
import { useModal } from "@/hooks/useModal";
import { X, Gear } from "@phosphor-icons/react";
import System from "@/models/system";
import showToast from "@/utils/toast";
import { useEffect, useState } from "react";

const NO_SETTINGS_NEEDED = ["default", "none"];
export default function AgentLLMItem({
  llm,
  availableLLMs,
  settings,
  checked,
  onClick,
}) {
  const { isOpen, openModal, closeModal } = useModal();
  const { name, value, logo, description } = llm;
  const [currentSettings, setCurrentSettings] = useState(settings);

  useEffect(() => {
    async function getSettings() {
      if (isOpen) {
        const _settings = await System.keys();
        setCurrentSettings(_settings ?? {});
      }
    }
    getSettings();
  }, [isOpen]);

  function handleProviderSelection() {
    // Determine if provider needs additional setup because its minimum required keys are
    // not yet set in settings.
    if (!checked) {
      const requiresAdditionalSetup = (llm.requiredConfig || []).some(
        (key) => !currentSettings[key]
      );
      if (requiresAdditionalSetup) {
        openModal();
        return;
      }
      onClick(value);
    }
  }

  return (
    <>
      <div
        onClick={handleProviderSelection}
        className={`w-full p-2 rounded-md hover:cursor-pointer hover:bg-[#F2F2F2] flex items-center justify-between ${checked ? "bg-[#E5E7EB]" : ""
          }`}
      >
        <div className="flex items-center gap-x-4 overflow-hidden">
          <input
            type="checkbox"
            value={value}
            className="peer w-4 h-4 text-[#252525] bg-white border-gray-300 rounded focus:ring-[#545454] shrink-0"
            checked={checked}
            readOnly={true}
            formNoValidate={true}
          />
          <img
            src={logo}
            alt={`${name} logo`}
            className="w-8 h-8 rounded-md shrink-0"
          />
          <div className="flex items-center gap-x-2 truncate">
            <span className="text-sm font-semibold text-[#252525] shrink-0">{name}</span>
            <span className="text-xs text-[#545454] truncate hidden sm:block">
              - {description}
            </span>
          </div>
        </div>
        {checked &&
          value !== "none" &&
          !NO_SETTINGS_NEEDED.includes(value) && (
            <button
              onClick={(e) => {
                e.preventDefault();
                openModal();
              }}
              className="border-none p-2 text-[#545454] hover:text-[#252525] hover:bg-[#F2F2F2] rounded-md transition-all duration-300 shrink-0"
              title="Edit Settings"
            >
              <Gear size={20} weight="bold" />
            </button>
          )}
      </div>
      <SetupProvider
        availableLLMs={availableLLMs}
        isOpen={isOpen}
        provider={value}
        closeModal={closeModal}
        postSubmit={onClick}
        settings={currentSettings}
      />
    </>
  );
}

function SetupProvider({
  availableLLMs,
  isOpen,
  provider,
  closeModal,
  postSubmit,
  settings,
}) {
  if (!isOpen) return null;
  const LLMOption = availableLLMs.find((llm) => llm.value === provider);
  if (!LLMOption) return null;

  async function handleUpdate(e) {
    e.preventDefault();
    e.stopPropagation();
    const data = {};
    const form = new FormData(e.target);
    for (var [key, value] of form.entries()) data[key] = value;
    const { error } = await System.updateSystem(data);
    if (error) {
      showToast(`Failed to save ${LLMOption.name} settings: ${error}`, "error");
      return;
    }

    closeModal();
    postSubmit();
    return false;
  }

  // Cannot do nested forms, it will cause all sorts of issues, so we portal this out
  // to the parent container form so we don't have nested forms.
  return createPortal(
    <ModalWrapper isOpen={isOpen}>
      <div className="fixed inset-0 z-50 overflow-auto bg-black bg-opacity-50 flex items-center justify-center">
        <div className="relative w-full max-w-2xl bg-white rounded-lg shadow border border-[#545454]">
          <div className="relative p-6 border-b rounded-t border-[#CFCFCF]">
            <div className="w-full flex gap-x-2 items-center">
              <h3 className="text-xl font-semibold text-[#252525] overflow-hidden overflow-ellipsis whitespace-nowrap">
                {LLMOption.name} Settings
              </h3>
            </div>
            <button
              onClick={closeModal}
              type="button"
              className="absolute top-4 right-4 transition-all duration-300 bg-transparent rounded-lg text-sm p-1 inline-flex items-center hover:bg-[#E5E7EB] border-transparent border"
            >
              <X size={24} weight="bold" className="text-[#545454]" />
            </button>
          </div>
          <form id="provider-form" onSubmit={handleUpdate}>
            <div className="px-7 py-6">
              <div className="space-y-6 max-h-[60vh] overflow-y-auto p-1">
                <p className="text-sm text-[#545454]">
                  To use {LLMOption.name} as this workspace's agent LLM you need
                  to set it up first.
                </p>
                <div>
                  {LLMOption.options(settings, { credentialsOnly: true })}
                </div>
              </div>
            </div>
            <div className="flex justify-between items-center mt-6 pt-6 border-t border-[#CFCFCF] px-7 pb-6">
              <button
                type="button"
                onClick={closeModal}
                className="transition-all duration-300 text-[#545454] hover:bg-[#F2F2F2] px-4 py-2 rounded-lg text-sm"
              >
                Cancel
              </button>
              <button
                type="submit"
                form="provider-form"
                className="transition-all duration-300 bg-[#252525] text-white hover:opacity-80 px-4 py-2 rounded-lg text-sm"
              >
                Save {LLMOption.name} settings
              </button>
            </div>
          </form>
        </div>
      </div>
    </ModalWrapper>,
    document.getElementById("workspace-agent-settings-container")
  );
}
