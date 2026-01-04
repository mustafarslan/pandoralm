import { useTranslation } from "react-i18next";

export default function MaxContextSnippets({ workspace, setHasChanges }) {
  const { t } = useTranslation();
  return (
    <div>
      <div className="flex flex-col">
        <label htmlFor="name" className="block input-label !text-[#252525]">
          {t("vector-workspace.snippets.title")}
        </label>
        <p className="text-[#545454] text-xs font-medium py-1.5">
          {t("vector-workspace.snippets.description")}
          <br />
          <i>{t("vector-workspace.snippets.recommend")}</i>
        </p>
      </div>
      <input
        name="topN"
        type="number"
        min={1}
        max={200}
        step={1}
        onWheel={(e) => e.target.blur()}
        defaultValue={workspace?.topN ?? 4}
        className="border border-[#545454] bg-white text-[#252525] placeholder:text-[#7D7D7D] text-sm rounded-lg focus:outline-none block w-full p-2.5 mt-2"
        placeholder="4"
        required={true}
        autoComplete="off"
        onChange={() => setHasChanges(true)}
      />
    </div>
  );
}
