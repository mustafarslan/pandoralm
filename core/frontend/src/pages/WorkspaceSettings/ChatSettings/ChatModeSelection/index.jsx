import { useState } from "react";
import { useTranslation } from "react-i18next";
export default function ChatModeSelection({ workspace, setHasChanges }) {
  const [chatMode, setChatMode] = useState(workspace?.chatMode || "chat");
  const { t } = useTranslation();
  return (
    <div>
      <div className="flex flex-col">
        <label htmlFor="chatMode" className="block input-label !text-[#252525]">
          {t("chat.mode.title")}
        </label>
      </div>

      <div className="flex flex-col gap-y-1 mt-2">
        <div className="w-fit flex gap-x-1 items-center p-1 rounded-lg bg-[#E5E7EB] border border-[#CFCFCF]">
          <input type="hidden" name="chatMode" value={chatMode} />
          <button
            type="button"
            disabled={chatMode === "chat"}
            onClick={() => {
              setChatMode("chat");
              setHasChanges(true);
            }}
            className="transition-bg duration-200 px-6 py-1 text-md text-[#545454] disabled:text-[#252525] bg-transparent disabled:bg-white disabled:shadow-sm rounded-md"
          >
            {t("chat.mode.chat.title")}
          </button>
          <button
            type="button"
            disabled={chatMode === "query"}
            onClick={() => {
              setChatMode("query");
              setHasChanges(true);
            }}
            className="transition-bg duration-200 px-6 py-1 text-md text-[#545454] disabled:text-[#252525] bg-transparent disabled:bg-white disabled:shadow-sm rounded-md"
          >
            {t("chat.mode.query.title")}
          </button>
        </div>
        <p className="text-sm text-[#545454]">
          {chatMode === "chat" ? (
            <>
              <b>{t("chat.mode.chat.title")}</b>{" "}
              {t("chat.mode.chat.desc-start")}{" "}
              <i className="font-semibold">{t("chat.mode.chat.and")}</i>{" "}
              {t("chat.mode.chat.desc-end")}
            </>
          ) : (
            <>
              <b>{t("chat.mode.query.title")}</b>{" "}
              {t("chat.mode.query.desc-start")}{" "}
              <i className="font-semibold">{t("chat.mode.query.only")}</i>{" "}
              {t("chat.mode.query.desc-end")}
            </>
          )}
        </p>
      </div>
    </div>
  );
}
