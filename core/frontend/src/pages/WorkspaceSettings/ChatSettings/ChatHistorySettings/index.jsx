import { useTranslation } from "react-i18next";
export default function ChatHistorySettings({ workspace, setHasChanges }) {
  const { t } = useTranslation();
  return (
    <div>
      <div className="flex flex-col gap-y-1 mb-4">
        <label htmlFor="name" className="block mb-2 input-label !text-[#252525]">
          {t("chat.history.title")}
        </label>
        <p className="text-[#545454] text-xs font-medium">
          {t("chat.history.desc-start")}
          <i> {t("chat.history.recommend")} </i>
          {t("chat.history.desc-end")}
        </p>
      </div>
      <input
        name="openAiHistory"
        type="number"
        min={1}
        max={45}
        step={1}
        onWheel={(e) => e.target.blur()}
        defaultValue={workspace?.openAiHistory ?? 20}
        className="border border-[#545454] bg-white text-[#252525] placeholder:text-[#7D7D7D] text-sm rounded-lg focus:outline-none block w-full p-2.5"
        placeholder="20"
        required={true}
        autoComplete="off"
        onChange={() => setHasChanges(true)}
      />
    </div>
  );
}
