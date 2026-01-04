import React, { useRef, useState } from "react";
import { X } from "@phosphor-icons/react";
import Workspace from "@/models/workspace";
import paths from "@/utils/paths";
import { useTranslation } from "react-i18next";
import ModalWrapper from "@/components/ModalWrapper";

const noop = () => false;
export default function NewWorkspaceModal({ hideModal = noop }) {
  const formEl = useRef(null);
  const [error, setError] = useState(null);
  const { t } = useTranslation();
  const handleCreate = async (e) => {
    setError(null);
    e.preventDefault();
    const data = {};
    const form = new FormData(formEl.current);
    for (var [key, value] of form.entries()) data[key] = value;
    const { workspace, message } = await Workspace.new(data);
    if (!!workspace) {
      window.location.href = paths.workspace.chat(workspace.slug);
    }
    setError(message);
  };

  return (
    <ModalWrapper isOpen={true}>
      <div className="w-full max-w-2xl bg-white rounded-lg shadow-xl border border-ink-border/20 overflow-hidden">
        <div className="relative p-6 border-b border-ink-border/10 bg-ink-panel/30">
          <div className="w-full flex gap-x-2 items-center">
            <h3 className="text-xl font-bold text-ink-heading overflow-hidden overflow-ellipsis whitespace-nowrap">
              {t("new-workspace.title")}
            </h3>
          </div>
          <button
            onClick={hideModal}
            type="button"
            className="absolute top-4 right-4 transition-all duration-300 bg-transparent rounded-lg text-sm p-1 inline-flex items-center hover:bg-ink-panel text-ink-muted hover:text-ink-primary"
          >
            <X size={24} weight="bold" />
          </button>
        </div>
        <div
          className="h-full w-full overflow-y-auto bg-ink-page"
          style={{ maxHeight: "calc(100vh - 200px)" }}
        >
          <form ref={formEl} onSubmit={handleCreate}>
            <div className="py-7 px-9 space-y-2 flex-col">
              <div className="w-full flex flex-col gap-y-4">
                <div>
                  <label
                    htmlFor="name"
                    className="block mb-2 text-sm font-medium text-ink-heading"
                  >
                    {t("common.workspaces-name")}
                  </label>
                  <input
                    name="name"
                    type="text"
                    id="name"
                    className="border-2 border-ink-border bg-white w-full text-ink-heading placeholder:text-ink-muted text-sm rounded-lg focus:outline-none focus:border-ink-action block w-full p-2.5 shadow-sm"
                    placeholder={t("new-workspace.placeholder")}
                    required={true}
                    autoComplete="off"
                    autoFocus={true}
                  />
                </div>
                {error && (
                  <p className="text-red-500 text-sm font-medium">Error: {error}</p>
                )}
              </div>
            </div>
            <div className="flex w-full justify-end items-center p-6 space-x-2 border-t border-ink-border/10 rounded-b bg-white">
              <button
                type="button"
                onClick={hideModal}
                className="transition-all duration-300 bg-transparent text-ink-muted hover:text-ink-heading px-4 py-2 rounded-lg text-sm font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="transition-all duration-300 bg-ink-action text-white hover:opacity-90 px-4 py-2 rounded-lg text-sm font-bold shadow-md hover:shadow-lg"
              >
                Create Workspace
              </button>
            </div>
          </form>
        </div>
      </div>
    </ModalWrapper>
  );
}

export function useNewWorkspaceModal() {
  const [showing, setShowing] = useState(false);
  const showModal = () => {
    setShowing(true);
  };
  const hideModal = () => {
    setShowing(false);
  };

  return { showing, showModal, hideModal };
}
