import { MagnifyingGlass, Check, CaretDown } from "@phosphor-icons/react";
import { useEffect, useState, useRef } from "react";
import OpenAiLogo from "@/media/llmprovider/openai.png";
import GenericOpenAiLogo from "@/media/llmprovider/generic-openai.png";
import AzureOpenAiLogo from "@/media/llmprovider/azure.png";
import AnthropicLogo from "@/media/llmprovider/anthropic.png";
import GeminiLogo from "@/media/llmprovider/gemini.png";
import OllamaLogo from "@/media/llmprovider/ollama.png";
import LMStudioLogo from "@/media/llmprovider/lmstudio.png";
import LocalAiLogo from "@/media/llmprovider/localai.png";
import TogetherAILogo from "@/media/llmprovider/togetherai.png";
import FireworksAILogo from "@/media/llmprovider/fireworksai.jpeg";
import MistralLogo from "@/media/llmprovider/mistral.jpeg";
import HuggingFaceLogo from "@/media/llmprovider/huggingface.png";
import PerplexityLogo from "@/media/llmprovider/perplexity.png";
import OpenRouterLogo from "@/media/llmprovider/openrouter.jpeg";
import GroqLogo from "@/media/llmprovider/groq.png";
import KoboldCPPLogo from "@/media/llmprovider/koboldcpp.png";
import TextGenWebUILogo from "@/media/llmprovider/text-generation-webui.png";
import LiteLLMLogo from "@/media/llmprovider/litellm.png";
import AWSBedrockLogo from "@/media/llmprovider/bedrock.png";
import DeepSeekLogo from "@/media/llmprovider/deepseek.png";
import APIPieLogo from "@/media/llmprovider/apipie.png";
import NovitaLogo from "@/media/llmprovider/novita.png";
import XAILogo from "@/media/llmprovider/xai.png";
import ZAiLogo from "@/media/llmprovider/zai.png";
import NvidiaNimLogo from "@/media/llmprovider/nvidia-nim.png";
import CohereLogo from "@/media/llmprovider/cohere.png";
import PPIOLogo from "@/media/llmprovider/ppio.png";
import DellProAiStudioLogo from "@/media/llmprovider/dpais.png";
import MoonshotAiLogo from "@/media/llmprovider/moonshotai.png";
import CometApiLogo from "@/media/llmprovider/cometapi.png";
import GiteeAILogo from "@/media/llmprovider/giteeai.png";

import OpenAiOptions from "@/components/LLMSelection/OpenAiOptions";
import GenericOpenAiOptions from "@/components/LLMSelection/GenericOpenAiOptions";
import AzureAiOptions from "@/components/LLMSelection/AzureAiOptions";
import AnthropicAiOptions from "@/components/LLMSelection/AnthropicAiOptions";
import LMStudioOptions from "@/components/LLMSelection/LMStudioOptions";
import LocalAiOptions from "@/components/LLMSelection/LocalAiOptions";
import GeminiLLMOptions from "@/components/LLMSelection/GeminiLLMOptions";
import OllamaLLMOptions from "@/components/LLMSelection/OllamaLLMOptions";
import MistralOptions from "@/components/LLMSelection/MistralOptions";
import HuggingFaceOptions from "@/components/LLMSelection/HuggingFaceOptions";
import TogetherAiOptions from "@/components/LLMSelection/TogetherAiOptions";
import FireworksAiOptions from "@/components/LLMSelection/FireworksAiOptions";
import PerplexityOptions from "@/components/LLMSelection/PerplexityOptions";
import OpenRouterOptions from "@/components/LLMSelection/OpenRouterOptions";
import GroqAiOptions from "@/components/LLMSelection/GroqAiOptions";
import CohereAiOptions from "@/components/LLMSelection/CohereAiOptions";
import KoboldCPPOptions from "@/components/LLMSelection/KoboldCPPOptions";
import TextGenWebUIOptions from "@/components/LLMSelection/TextGenWebUIOptions";
import LiteLLMOptions from "@/components/LLMSelection/LiteLLMOptions";
import AWSBedrockLLMOptions from "@/components/LLMSelection/AwsBedrockLLMOptions";
import DeepSeekOptions from "@/components/LLMSelection/DeepSeekOptions";
import ApiPieLLMOptions from "@/components/LLMSelection/ApiPieOptions";
import NovitaLLMOptions from "@/components/LLMSelection/NovitaLLMOptions";
import XAILLMOptions from "@/components/LLMSelection/XAiLLMOptions";
import ZAiLLMOptions from "@/components/LLMSelection/ZAiLLMOptions";
import NvidiaNimOptions from "@/components/LLMSelection/NvidiaNimOptions";
import PPIOLLMOptions from "@/components/LLMSelection/PPIOLLMOptions";
import DellProAiStudioOptions from "@/components/LLMSelection/DPAISOptions";
import MoonshotAiOptions from "@/components/LLMSelection/MoonshotAiOptions";
import CometApiLLMOptions from "@/components/LLMSelection/CometApiLLMOptions";
import GiteeAiOptions from "@/components/LLMSelection/GiteeAIOptions";

import System from "@/models/system";
import paths from "@/utils/paths";
import showToast from "@/utils/toast";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

const LLMS = [
  {
    name: "OpenAI",
    value: "openai",
    logo: OpenAiLogo,
    options: (settings) => <OpenAiOptions settings={settings} />,
    description: "The standard option for most non-commercial use.",
  },
  {
    name: "Azure OpenAI",
    value: "azure",
    logo: AzureOpenAiLogo,
    options: (settings) => <AzureAiOptions settings={settings} />,
    description: "The enterprise option of OpenAI hosted on Azure services.",
  },
  {
    name: "Anthropic",
    value: "anthropic",
    logo: AnthropicLogo,
    options: (settings) => <AnthropicAiOptions settings={settings} />,
    description: "A friendly AI Assistant hosted by Anthropic.",
  },
  {
    name: "Gemini",
    value: "gemini",
    logo: GeminiLogo,
    options: (settings) => <GeminiLLMOptions settings={settings} />,
    description: "Google's largest and most capable AI model",
  },
  {
    name: "NVIDIA NIM",
    value: "nvidia-nim",
    logo: NvidiaNimLogo,
    options: (settings) => <NvidiaNimOptions settings={settings} />,
    description:
      "Run full parameter LLMs directly on your NVIDIA RTX GPU using NVIDIA NIM.",
  },
  {
    name: "HuggingFace",
    value: "huggingface",
    logo: HuggingFaceLogo,
    options: (settings) => <HuggingFaceOptions settings={settings} />,
    description:
      "Access 150,000+ open-source LLMs and the world's AI community",
  },
  {
    name: "Ollama",
    value: "ollama",
    logo: OllamaLogo,
    options: (settings) => <OllamaLLMOptions settings={settings} />,
    description: "Run LLMs locally on your own machine.",
  },
  {
    name: "Dell Pro AI Studio",
    value: "dpais",
    logo: DellProAiStudioLogo,
    options: (settings) => <DellProAiStudioOptions settings={settings} />,
    description:
      "Run powerful LLMs quickly on NPU powered by Dell Pro AI Studio.",
  },
  {
    name: "LM Studio",
    value: "lmstudio",
    logo: LMStudioLogo,
    options: (settings) => <LMStudioOptions settings={settings} />,
    description:
      "Discover, download, and run thousands of cutting edge LLMs in a few clicks.",
  },
  {
    name: "Local AI",
    value: "localai",
    logo: LocalAiLogo,
    options: (settings) => <LocalAiOptions settings={settings} />,
    description: "Run LLMs locally on your own machine.",
  },
  {
    name: "Novita AI",
    value: "novita",
    logo: NovitaLogo,
    options: (settings) => <NovitaLLMOptions settings={settings} />,
    description:
      "Reliable, Scalable, and Cost-Effective for LLMs from Novita AI",
  },
  {
    name: "KoboldCPP",
    value: "koboldcpp",
    logo: KoboldCPPLogo,
    options: (settings) => <KoboldCPPOptions settings={settings} />,
    description: "Run local LLMs using koboldcpp.",
  },
  {
    name: "Oobabooga Web UI",
    value: "textgenwebui",
    logo: TextGenWebUILogo,
    options: (settings) => <TextGenWebUIOptions settings={settings} />,
    description: "Run local LLMs using Oobabooga's Text Generation Web UI.",
  },
  {
    name: "Together AI",
    value: "togetherai",
    logo: TogetherAILogo,
    options: (settings) => <TogetherAiOptions settings={settings} />,
    description: "Run open source models from Together AI.",
  },
  {
    name: "Fireworks AI",
    value: "fireworksai",
    logo: FireworksAILogo,
    options: (settings) => <FireworksAiOptions settings={settings} />,
    description:
      "The fastest and most efficient inference engine to build production-ready, compound AI systems.",
  },
  {
    name: "Mistral",
    value: "mistral",
    logo: MistralLogo,
    options: (settings) => <MistralOptions settings={settings} />,
    description: "Run open source models from Mistral AI.",
  },
  {
    name: "Perplexity AI",
    value: "perplexity",
    logo: PerplexityLogo,
    options: (settings) => <PerplexityOptions settings={settings} />,
    description:
      "Run powerful and internet-connected models hosted by Perplexity AI.",
  },
  {
    name: "OpenRouter",
    value: "openrouter",
    logo: OpenRouterLogo,
    options: (settings) => <OpenRouterOptions settings={settings} />,
    description: "A unified interface for LLMs.",
  },
  {
    name: "Groq",
    value: "groq",
    logo: GroqLogo,
    options: (settings) => <GroqAiOptions settings={settings} />,
    description:
      "The fastest LLM inferencing available for real-time AI applications.",
  },
  {
    name: "Cohere",
    value: "cohere",
    logo: CohereLogo,
    options: (settings) => <CohereAiOptions settings={settings} />,
    description: "Run Cohere's powerful Command models.",
  },
  {
    name: "LiteLLM",
    value: "litellm",
    logo: LiteLLMLogo,
    options: (settings) => <LiteLLMOptions settings={settings} />,
    description: "Run LiteLLM's OpenAI compatible proxy for various LLMs.",
  },
  {
    name: "DeepSeek",
    value: "deepseek",
    logo: DeepSeekLogo,
    options: (settings) => <DeepSeekOptions settings={settings} />,
    description: "Run DeepSeek's powerful LLMs.",
  },
  {
    name: "PPIO",
    value: "ppio",
    logo: PPIOLogo,
    options: (settings) => <PPIOLLMOptions settings={settings} />,
    description:
      "Run stable and cost-efficient open-source LLM APIs, such as DeepSeek, Llama, Qwen etc.",
  },
  {
    name: "APIpie",
    value: "apipie",
    logo: APIPieLogo,
    options: (settings) => <ApiPieLLMOptions settings={settings} />,
    description: "A unified API of AI services from leading providers",
  },
  {
    name: "Generic OpenAI",
    value: "generic-openai",
    logo: GenericOpenAiLogo,
    options: (settings) => <GenericOpenAiOptions settings={settings} />,
    description:
      "Connect to any OpenAi-compatible service via a custom configuration",
  },
  {
    name: "AWS Bedrock",
    value: "bedrock",
    logo: AWSBedrockLogo,
    options: (settings) => <AWSBedrockLLMOptions settings={settings} />,
    description: "Run powerful foundation models privately with AWS Bedrock.",
  },
  {
    name: "xAI",
    value: "xai",
    logo: XAILogo,
    options: (settings) => <XAILLMOptions settings={settings} />,
    description: "Run xAI's powerful LLMs like Grok-2 and more.",
  },
  {
    name: "Z.AI",
    value: "zai",
    logo: ZAiLogo,
    options: (settings) => <ZAiLLMOptions settings={settings} />,
    description: "Run Z.AI's powerful GLM models.",
  },
  {
    name: "Moonshot AI",
    value: "moonshotai",
    logo: MoonshotAiLogo,
    options: (settings) => <MoonshotAiOptions settings={settings} />,
    description: "Run Moonshot AI's powerful LLMs.",
  },
  {
    name: "CometAPI",
    value: "cometapi",
    logo: CometApiLogo,
    options: (settings) => <CometApiLLMOptions settings={settings} />,
    description: "500+ AI Models all in one API.",
  },
  {
    name: "GiteeAI",
    value: "giteeai",
    logo: GiteeAILogo,
    options: (settings) => <GiteeAiOptions settings={settings} />,
    description: "Run GiteeAI's powerful LLMs.",
  },
];

export default function LLMPreference({
  setHeader,
  setForwardBtn,
  setBackBtn,
}) {
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredLLMs, setFilteredLLMs] = useState([]);
  const [selectedLLM, setSelectedLLM] = useState(null);
  const [settings, setSettings] = useState(null);
  const formRef = useRef(null);
  const hiddenSubmitButtonRef = useRef(null);
  const isHosted = window.location.hostname.includes("useanything.com");
  const navigate = useNavigate();

  const TITLE = t("onboarding.llm.title");
  const DESCRIPTION = t("onboarding.llm.description");

  useEffect(() => {
    async function fetchKeys() {
      const _settings = await System.keys();
      setSettings(_settings);
      setSelectedLLM(_settings?.LLMProvider || "openai");
    }
    fetchKeys();
  }, []);

  function handleForward() {
    if (hiddenSubmitButtonRef.current) {
      hiddenSubmitButtonRef.current.click();
    }
  }

  function handleBack() {
    navigate(paths.onboarding.home());
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    /** @type {HTMLFormElement} */
    const form = e.target;
    // We created a new object to send to the backend
    const data = {};
    const formData = new FormData(form);

    // Manual overrides from non-input state
    data.LLMProvider = selectedLLM;
    data.EmbeddingEngine = "native";
    data.VectorDB = "lancedb";

    for (var [key, value] of formData.entries()) {
      if (key === 'LLMProvider') continue;
      data[key] = value;
    }

    const { error } = await System.updateSystem(data);
    if (error) {
      showToast(`Failed to save LLM settings: ${error}`, "error");
      return;
    }
    navigate(paths.onboarding.userSetup());
  };

  useEffect(() => {
    setForwardBtn({ showing: true, disabled: false, onClick: handleForward });
    setBackBtn({ showing: true, disabled: false, onClick: handleBack });
  }, []);

  useEffect(() => {
    const filtered = LLMS.filter((llm) =>
      llm.name.toLowerCase().includes(searchQuery.toLowerCase())
    );
    setFilteredLLMs(filtered);
  }, [searchQuery, selectedLLM]);

  return (
    // Outer Transparent Wrapper
    <div className="w-full flex justify-center bg-transparent">
      {/* Inner Content Card (Ink Wash Style: shadow-xl, border-[#E5E5E5]) */}
      <div className="bg-white shadow-xl border border-[#E5E5E5] rounded-xl p-8 max-w-3xl w-full z-10 relative flex flex-col gap-8 animate-in fade-in slide-in-from-bottom-4 duration-500">

        {/* Header: Centered */}
        <div className="text-center w-full">
          <h2 className="text-[#252525] font-bold text-2xl mb-1">
            {TITLE}
          </h2>
          <p className="text-[#545454] text-sm">
            PandoraLM can work with both hosted and local LLMs.
          </p>
        </div>

        <form ref={formRef} onSubmit={handleSubmit} className="flex flex-col gap-8">

          {/* Search Bar (Drafting Field) */}
          <div className="relative">
            <MagnifyingGlass
              size={18}
              weight="bold"
              className="absolute left-4 top-1/2 -translate-y-1/2 text-[#7D7D7D]"
            />
            <input
              type="text"
              placeholder="Search LLM providers"
              className="w-full pl-11 pr-4 py-2 bg-white border-2 border-[#7D7D7D] rounded-full text-[#252525] placeholder:text-[#7D7D7D] outline-none focus:border-[#252525] transition-colors"
              onChange={(e) => setSearchQuery(e.target.value)}
              autoComplete="off"
              onKeyDown={(e) => {
                if (e.key === "Enter") e.preventDefault();
              }}
            />
          </div>

          {/* Provider Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[350px] overflow-y-auto pr-2 custom-scrollbar">
            {filteredLLMs.map((llm) => {
              if (llm.value === "native" && isHosted) return null;
              const isSelected = selectedLLM === llm.value;
              return (
                <div
                  key={llm.value}
                  onClick={() => setSelectedLLM(llm.value)}
                  className={`
                        relative p-4 rounded-lg border cursor-pointer transition-all duration-200 group
                        ${isSelected
                      ? 'bg-[#252525] border-[#252525] text-white shadow-md'
                      : 'bg-white border-[#7D7D7D] text-[#252525] hover:bg-[#F2F2F2] hover:border-[#252525]'
                    }
                      `}
                >
                  {/* Selection Checkbox */}
                  <div className={`
                        absolute top-4 right-4 w-5 h-5 rounded flex items-center justify-center border transition-colors
                        ${isSelected ? 'bg-white border-white' : 'bg-white border-[#7D7D7D]'}
                      `}>
                    {isSelected && <Check weight="bold" className="text-[#252525] text-xs" />}
                  </div>

                  <div className="flex items-center gap-3 mb-2">
                    <div className={`p-1 rounded bg-white ${isSelected ? '' : 'border border-gray-100'}`}>
                      <img src={llm.logo} alt={llm.name} className="w-8 h-8 object-contain" />
                    </div>
                    <span className="font-bold text-sm">{llm.name}</span>
                  </div>

                  <p className={`text-xs pr-6 ${isSelected ? 'text-gray-300' : 'text-[#545454]'}`}>
                    {llm.description}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Advanced Settings (Drafting Fields) */}
          {selectedLLM && (
            <div className="animate-fade-in">
              <div className="border-t border-[#E5E5E5] my-2 pt-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-[#252525] font-bold text-xs uppercase tracking-wider">Configuration</span>
                </div>

                <div className="
                        [&_input]:bg-white [&_input]:border-2 [&_input]:border-[#7D7D7D] [&_input]:text-[#252525] [&_input]:rounded-lg [&_input]:px-3 [&_input]:py-2 [&_input]:outline-none [&_input]:focus:border-[#252525] [&_input]:w-full
                        [&_select]:bg-white [&_select]:border-2 [&_select]:border-[#7D7D7D] [&_select]:text-[#252525] [&_select]:rounded-lg [&_select]:px-3 [&_select]:py-2 [&_select]:outline-none [&_select]:focus:border-[#252525] [&_select]:w-full
                        [&_textarea]:bg-white [&_textarea]:border-2 [&_textarea]:border-[#7D7D7D] [&_textarea]:text-[#252525] [&_textarea]:rounded-lg [&_textarea]:px-3 [&_textarea]:py-2 [&_textarea]:outline-none [&_textarea]:focus:border-[#252525] [&_textarea]:w-full
                        [&_label]:text-[#252525] [&_label]:font-bold [&_label]:text-xs [&_label]:uppercase [&_label]:mb-1 [&_label]:block
                        flex flex-col gap-4
                     ">
                  {LLMS.find((llm) => llm.value === selectedLLM)?.options(settings)}
                </div>
              </div>
            </div>
          )}

          <button
            type="submit"
            ref={hiddenSubmitButtonRef}
            hidden
            aria-hidden="true"
          ></button>
        </form>
      </div>
    </div>
  );
}
