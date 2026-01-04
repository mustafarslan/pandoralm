import { useTranslation } from "react-i18next";

export default function VectorDBIdentifier({ workspace }) {
  const { t } = useTranslation();
  return (
    <div>
      <h3 className="input-label !text-[#252525]">{t("vector-workspace.identifier")}</h3>
      <p className="text-[#545454] text-xs font-medium py-1"> </p>
      <p className="text-[#545454] text-sm">{workspace?.slug}</p>
    </div>
  );
}
