import { ABORT_STREAM_EVENT } from "@/utils/chat";
import { Tooltip } from "react-tooltip";
import { StopCircle } from "@phosphor-icons/react";

export default function StopGenerationButton() {
  function emitHaltEvent() {
    window.dispatchEvent(new CustomEvent(ABORT_STREAM_EVENT));
  }

  return (
    <>
      <button
        type="button"
        onClick={emitHaltEvent}
        data-tooltip-id="stop-generation-button"
        data-tooltip-content="Stop generating response"
        className="border-none inline-flex items-center justify-center leading-none rounded-2xl cursor-pointer opacity-60 hover:opacity-100 light:opacity-100 light:hover:opacity-60 ml-4 group"
        aria-label="Stop generating"
      >
        <StopCircle
          color="#252525"
          className="w-[22px] h-[22px] pointer-events-none text-[#252525]"
          weight="fill"
        />
      </button>
      <Tooltip
        id="stop-generation-button"
        place="bottom"
        delayShow={300}
        className="tooltip !text-xs z-99 -ml-1"
      />
    </>
  );
}
