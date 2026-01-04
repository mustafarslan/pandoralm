import { CloudArrowUp } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import showToast from "../../../../../utils/toast";
import System from "../../../../../models/system";
import { useDropzone } from "react-dropzone";
import { v4 } from "uuid";
import FileUploadProgress from "./FileUploadProgress";
import Workspace from "../../../../../models/workspace";
import debounce from "lodash.debounce";

export default function UploadFile({
  workspace,
  fetchKeys,
  setLoading,
  setLoadingMessage,
}) {
  const { t } = useTranslation();
  const [ready, setReady] = useState(false);
  const [files, setFiles] = useState([]);
  const [fetchingUrl, setFetchingUrl] = useState(false);
  const [selectedLayer, setSelectedLayer] = useState("user");

  const handleSendLink = async (e) => {
    e.preventDefault();
    setLoading(true);
    setLoadingMessage("Scraping link...");
    setFetchingUrl(true);
    const formEl = e.target;
    const form = new FormData(formEl);
    const { response, data } = await Workspace.uploadLink(
      workspace.slug,
      form.get("link")
    );
    if (!response.ok) {
      showToast(`Error uploading link: ${data.error}`, "error");
    } else {
      fetchKeys(true);
      showToast("Link uploaded successfully", "success");
      formEl.reset();
    }
    setLoading(false);
    setFetchingUrl(false);
  };

  // Queue all fetchKeys calls through the same debouncer to prevent spamming the server.
  // either a success or error will trigger a fetchKeys call so the UI is not stuck loading.
  const debouncedFetchKeys = debounce(() => fetchKeys(true), 1000);
  const handleUploadSuccess = () => debouncedFetchKeys();
  const handleUploadError = () => debouncedFetchKeys();

  const onDrop = async (acceptedFiles, rejections) => {
    const newAccepted = acceptedFiles.map((file) => {
      return {
        uid: v4(),
        file,
      };
    });
    const newRejected = rejections.map((file) => {
      return {
        uid: v4(),
        file: file.file,
        rejected: true,
        reason: file.errors[0].code,
      };
    });
    setFiles([...newAccepted, ...newRejected]);
  };

  useEffect(() => {
    async function checkProcessorOnline() {
      const online = await System.checkDocumentProcessorOnline();
      setReady(online);
    }
    checkProcessorOnline();
  }, []);

  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    disabled: !ready,
  });

  return (
    <div>
      {/* Knowledge Layer Selector */}
      <div className="mb-4">
        <label className="block text-xs font-bold text-[#252525] uppercase tracking-widest mb-2">
          Knowledge Layer
        </label>
        <select
          value={selectedLayer}
          onChange={(e) => setSelectedLayer(e.target.value)}
          className="w-full bg-[#FFFFFF] border border-[#545454] rounded-lg p-2.5 text-[#252525] text-sm focus:outline-none focus:border-[#252525] transition-colors appearance-none"
        >
          <option value="system">System (Global)</option>
          <option value="organization">Organization (All Teams)</option>
          <option value="team">Team (Specific Group)</option>
          <option value="user">User (Private)</option>
        </select>
      </div>

      <div
        className={`w-[560px] border-dashed border-[2px] rounded-2xl transition-colors duration-300 p-3 flex flex-col justify-center ${ready
          ? "border-[#545454] bg-[#FAFAFA] cursor-pointer hover:bg-[#F0F0F0]"
          : "border-[#545454] bg-[#FAFAFA] opacity-50 cursor-not-allowed"
          }`}
        {...getRootProps()}
      >
        <input {...getInputProps()} />
        {ready === false ? (
          <div className="flex flex-col items-center justify-center h-full py-6">
            <CloudArrowUp className="w-8 h-8 text-[#7D7D7D]" />
            <div className="text-[#252525] text-sm font-semibold py-1">
              {t("connectors.upload.processor-offline")}
            </div>
            <div className="text-[#7D7D7D] text-xs font-medium py-1 px-20 text-center">
              {t("connectors.upload.processor-offline-desc")}
            </div>
          </div>
        ) : files.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-6">
            <CloudArrowUp className="w-8 h-8 text-[#252525]" />
            <div className="text-[#252525] text-sm font-semibold py-1">
              {t("connectors.upload.click-upload")}
            </div>
            <div className="text-[#7D7D7D] text-xs font-medium py-1">
              {t("connectors.upload.file-types")}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2 overflow-auto max-h-[180px] p-1 overflow-y-scroll no-scroll">
            {files.map((file) => (
              <FileUploadProgress
                key={file.uid}
                file={file.file}
                uuid={file.uid}
                setFiles={setFiles}
                slug={workspace.slug}
                rejected={file?.rejected}
                reason={file?.reason}
                onUploadSuccess={handleUploadSuccess}
                onUploadError={handleUploadError}
                setLoading={setLoading}
                setLoadingMessage={setLoadingMessage}
                layerId={selectedLayer}
              />
            ))}
          </div>
        )}
      </div>
      <div className="text-center text-[#7D7D7D] text-xs font-medium w-[560px] py-2">
        {t("connectors.upload.or-submit-link")}
      </div>
      <form onSubmit={handleSendLink} className="flex gap-x-2">
        <input
          disabled={fetchingUrl}
          name="link"
          type="url"
          className="border border-[#545454] disabled:bg-[#FAFAFA] disabled:text-[#7D7D7D] bg-[#FFFFFF] text-[#252525] placeholder:text-[#7D7D7D] text-sm rounded-lg focus:outline-none focus:border-[#252525] block w-3/4 p-2.5"
          placeholder={t("connectors.upload.placeholder-link")}
          autoComplete="off"
        />
        <button
          disabled={fetchingUrl}
          type="submit"
          className="disabled:bg-white/20 disabled:text-slate-300 disabled:border-slate-400 disabled:cursor-wait bg bg-transparent hover:bg-[#252525] hover:text-[#FFFFFF] w-auto border border-[#545454] text-sm text-[#252525] p-2.5 rounded-lg transition-colors font-medium"
        >
          {fetchingUrl
            ? t("connectors.upload.fetching")
            : t("connectors.upload.fetch-website")}
        </button>
      </form>
      <div className="mt-6 text-center text-[#7D7D7D] text-xs font-medium w-[560px]">
        {t("connectors.upload.privacy-notice")}
      </div>
    </div>
  );
}
