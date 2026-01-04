import React, { memo, useState } from "react";
import useCopyText from "@/hooks/useCopyText";
import { Check, ThumbsUp, ArrowsClockwise, Copy, Star } from "@phosphor-icons/react";
import Workspace from "@/models/workspace";
import { EditMessageAction } from "./EditMessage";
import RenderMetrics from "./RenderMetrics";
import ActionMenu from "./ActionMenu";
import { useTranslation } from "react-i18next";
import { cortexPost } from "@/utils/cortexApi";
import showToast from "@/utils/toast";

const Actions = ({
  message,
  feedbackScore,
  chatId,
  slug,
  isLastMessage,
  regenerateMessage,
  forkThread,
  isEditing,
  role,
  metrics = {},
  alignmentCls = "",
}) => {
  const { t } = useTranslation();
  const [selectedFeedback, setSelectedFeedback] = useState(feedbackScore);
  const handleFeedback = async (newFeedback) => {
    const updatedFeedback =
      selectedFeedback === newFeedback ? null : newFeedback;
    await Workspace.updateChatFeedback(chatId, slug, updatedFeedback);
    setSelectedFeedback(updatedFeedback);
  };

  return (
    <div className={`flex w-full justify-between items-center ${alignmentCls}`}>
      <div className="flex justify-start items-center gap-x-[8px]">
        <CopyMessage message={message} />
        <div className="md:group-hover:opacity-100 transition-all duration-300 md:opacity-0 flex justify-start items-center gap-x-[8px]">
          <EditMessageAction
            chatId={chatId}
            role={role}
            isEditing={isEditing}
          />
          {isLastMessage && !isEditing && (
            <RegenerateMessage
              regenerateMessage={regenerateMessage}
              slug={slug}
              chatId={chatId}
            />
          )}
          {chatId && role !== "user" && !isEditing && (
            <FeedbackButton
              isSelected={selectedFeedback === true}
              handleFeedback={() => handleFeedback(true)}
              tooltipId="feedback-button"
              tooltipContent={t("chat_window.good_response")}
              IconComponent={ThumbsUp}
            />
          )}
          {chatId && role !== "user" && !isEditing && (
            <AddToGoldStandard message={message} />
          )}
          <ActionMenu
            chatId={chatId}
            forkThread={forkThread}
            isEditing={isEditing}
            role={role}
          />
        </div>
      </div>
      <RenderMetrics metrics={metrics} />
    </div>
  );
};

function FeedbackButton({
  isSelected,
  handleFeedback,
  tooltipContent,
  IconComponent,
}) {
  return (
    <div className="mt-3 relative">
      <button
        onClick={handleFeedback}
        data-tooltip-id="feedback-button"
        data-tooltip-content={tooltipContent}
        className="text-zinc-300"
        aria-label={tooltipContent}
      >
        <IconComponent
          color="var(--theme-sidebar-footer-icon-fill)"
          size={20}
          className="mb-1"
          weight={isSelected ? "fill" : "regular"}
        />
      </button>
    </div>
  );
}

function AddToGoldStandard({ message }) {
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    if (saved || loading) return;
    setLoading(true);
    try {
      await cortexPost('/api/v1/evaluation/gold-standard/add', {
        query: "(User query context pending)",
        response: message
      });
      setSaved(true);
      showToast("Added to Gold Standard Queue", "success");
    } catch (e) {
      console.error(e);
      showToast("Failed to add to queue", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-3 relative">
      <button
        onClick={handleSave}
        data-tooltip-id="gold-standard-btn"
        data-tooltip-content={saved ? "Queued for Gold Standard" : "Save to Gold Standard"}
        className="text-zinc-300"
      >
        <Star
          color={saved ? "#fbbf24" : "var(--theme-sidebar-footer-icon-fill)"}
          size={20}
          className="mb-1"
          weight={saved ? "fill" : "regular"}
        />
      </button>
    </div>
  );
}

function CopyMessage({ message }) {
  const { copied, copyText } = useCopyText();
  const { t } = useTranslation();

  return (
    <>
      <div className="mt-3 relative">
        <button
          onClick={() => copyText(message)}
          data-tooltip-id="copy-assistant-text"
          data-tooltip-content={t("chat_window.copy")}
          className="text-zinc-300"
          aria-label={t("chat_window.copy")}
        >
          {copied ? (
            <Check
              color="var(--theme-sidebar-footer-icon-fill)"
              size={20}
              className="mb-1"
            />
          ) : (
            <Copy
              color="var(--theme-sidebar-footer-icon-fill)"
              size={20}
              className="mb-1"
            />
          )}
        </button>
      </div>
    </>
  );
}

function RegenerateMessage({ regenerateMessage, chatId }) {
  if (!chatId) return null;
  const { t } = useTranslation();
  return (
    <div className="mt-3 relative">
      <button
        onClick={() => regenerateMessage(chatId)}
        data-tooltip-id="regenerate-assistant-text"
        data-tooltip-content={t("chat_window.regenerate_response")}
        className="border-none text-zinc-300"
        aria-label={t("chat_window.regenerate")}
      >
        <ArrowsClockwise
          color="var(--theme-sidebar-footer-icon-fill)"
          size={20}
          className="mb-1"
          weight="fill"
        />
      </button>
    </div>
  );
}

export default memo(Actions);
