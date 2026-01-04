import { ArrowLeft, ArrowRight } from "@phosphor-icons/react";
import NeuralGraph from "@/components/Onboarding/Visuals/NeuralGraph";
import { useState } from "react";
import { isMobile } from "react-device-detect";
import Home from "./Home";
import LLMPreference from "./LLMPreference";
import UserSetup from "./UserSetup";
import DataHandling from "./DataHandling";
import Survey from "./Survey";
import CreateWorkspace from "./CreateWorkspace";

const OnboardingSteps = {
  home: Home,
  "llm-preference": LLMPreference,
  "user-setup": UserSetup,
  "data-handling": DataHandling,
  survey: Survey,
  "create-workspace": CreateWorkspace,
};

export default OnboardingSteps;

export function OnboardingLayout({ children }) {
  const [header, setHeader] = useState({
    title: "",
    description: "",
  });
  const [backBtn, setBackBtn] = useState({
    showing: false,
    disabled: true,
    onClick: () => null,
  });
  const [forwardBtn, setForwardBtn] = useState({
    showing: false,
    disabled: true,
    onClick: () => null,
  });

  if (isMobile) {
    return (
      <div
        data-layout="onboarding"
        className="w-screen h-screen overflow-y-auto bg-theme-bg-primary overflow-hidden"
      >
        <div className="flex flex-col">
          <div className="w-full relative py-10 px-2">
            <div className="flex flex-col w-fit mx-auto gap-y-1 mb-[55px]">
              <h1 className="text-ink-heading font-semibold text-center text-2xl">
                {header.title}
              </h1>
              <p className="text-ink-muted text-base text-center">
                {header.description}
              </p>
            </div>
            {children(setHeader, setBackBtn, setForwardBtn)}
          </div>
          <div className="flex w-full justify-center gap-x-4 pb-20">
            <div className="flex justify-center items-center">
              {backBtn.showing && (
                <button
                  disabled={backBtn.disabled}
                  onClick={backBtn.onClick}
                  className="group p-2 rounded-lg border-2 border-zinc-300 disabled:border-zinc-600 h-fit w-fit disabled:not-allowed hover:bg-zinc-100 disabled:hover:bg-transparent"
                >
                  <ArrowLeft
                    className="text-white group-hover:text-black group-disabled:text-gray-500"
                    size={30}
                  />
                </button>
              )}
            </div>

            <div className="flex justify-center items-center">
              {forwardBtn.showing && (
                <button
                  disabled={forwardBtn.disabled}
                  onClick={forwardBtn.onClick}
                  className="group p-2 rounded-lg border-2 border-zinc-300 disabled:border-zinc-600 h-fit w-fit disabled:not-allowed hover:bg-teal disabled:hover:bg-transparent"
                >
                  <ArrowRight
                    className="text-white group-hover:text-teal group-disabled:text-gray-500"
                    size={30}
                  />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Persistent Stage Layout for Desktop
  // Removed restrictive h-full and used min-h-screen/flex-grow for safe centering
  return (
    <div className="relative w-full min-h-screen bg-[#F2F2F2]">
      {/* Persistent Background Layer (z-0) - FIXED positioning */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <NeuralGraph position="bottom-right" />
        <NeuralGraph position="top-right" />
      </div>

      {/* Content Stage (z-10) */}
      <div className="relative z-10 w-full min-h-screen flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-7xl flex-grow flex items-center justify-center">
          {/* Left Arrow */}
          <div className="hidden md:flex w-[80px] items-center justify-center">
            {backBtn.showing && (
              <button
                disabled={backBtn.disabled}
                onClick={backBtn.onClick}
                className="p-3 rounded-full hover:bg-black/5 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ArrowLeft size={32} className="text-[#252525]" />
              </button>
            )}
          </div>

          {/* Center Stage - flexible height, padded to prevent clipping */}
          <div className="flex-1 w-full flex flex-col items-center justify-center min-w-0 py-10">
            {children(setHeader, setBackBtn, setForwardBtn)}
          </div>

          {/* Right Arrow */}
          <div className="hidden md:flex w-[80px] items-center justify-center">
            {forwardBtn.showing && (
              <button
                disabled={forwardBtn.disabled}
                onClick={forwardBtn.onClick}
                className="p-3 rounded-full hover:bg-black/5 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ArrowRight size={32} className="text-[#252525]" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
