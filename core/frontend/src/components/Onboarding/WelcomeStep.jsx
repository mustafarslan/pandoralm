import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import paths from '@/utils/paths';

const WelcomeStep = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();

  return (
    <div className="relative z-10 flex justify-center items-center">
      <div className="bg-white border border-gray-100 rounded-2xl p-12 flex flex-col items-center justify-center max-w-lg w-full text-center shadow-sm">
        <p className="text-[#545454] text-sm font-semibold uppercase tracking-widest mb-1">
          {t("onboarding.home.title")}
        </p>
        <h1 className="text-[#252525] text-5xl font-extrabold tracking-tight mb-8 mt-2">
          PandoraLM
        </h1>
        <button
          onClick={() => navigate(paths.onboarding.llmPreference())}
          className="w-full md:w-auto md:px-8 py-3 rounded-md font-medium text-white bg-[#252525] hover:bg-[#333333] hover:scale-[1.02] transition-all duration-200 shadow-lg"
        >
          {t("onboarding.home.getStarted")}
        </button>
      </div>
    </div>
  );
};

export default WelcomeStep;
