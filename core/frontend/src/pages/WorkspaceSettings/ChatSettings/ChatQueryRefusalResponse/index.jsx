import { chatQueryRefusalResponse } from "@/utils/chat";
import { useTranslation } from "react-i18next";
export default function ChatQueryRefusalResponse({ workspace, setHasChanges }) {
  const { t } = useTranslation();
  return (
    <div>
      <div className="flex flex-col">
        <label htmlFor="name" className="block input-label !text-[#252525]">
          {t("chat.refusal.title")}
        </label>
        <p className="text-[#545454] text-xs font-medium py-1.5">
          {t("chat.refusal.desc-start")}{" "}
          <code className="border border-[#CFCFCF] bg-[#F2F2F2] text-[#252525] p-0.5 rounded-sm">
            {t("chat.refusal.query")}
          </code>{" "}
          {t("chat.refusal.desc-end")}
        </p>
      </div>
      <textarea
        name="queryRefusalResponse"
        rows={2}
        defaultValue={chatQueryRefusalResponse(workspace)}
        className="border border-[#545454] bg-white placeholder:text-[#7D7D7D] text-[#252525] text-sm rounded-lg focus:outline-none block w-full p-2.5 mt-2"
        placeholder="The text returned in query mode when there is no relevant context found for a response."
        required={true}
        wrap="soft"
        autoComplete="off"
        onChange={() => setHasChanges(true)}
      />
    </div>
  );
}
