
import React from 'react';
import OpenAIView from "./OpenAiOptions";
import AzureOpenAIView from "./AzureAiOptions";
import AnthropicAiView from "./AnthropicAiOptions";
import OllamaLLMView from "./OllamaLLMOptions";
import LMStudioView from "./LMStudioOptions";
import LocalAiView from "./LocalAiOptions";
import TogetherAiView from "./TogetherAiOptions";
import FireworksAiView from "./FireworksAiOptions";
import MistralView from "./MistralOptions";
import HuggingFaceView from "./HuggingFaceOptions";
import PerplexityView from "./PerplexityOptions";
import OpenRouterView from "./OpenRouterOptions";
import NativeLLMView from "./GenericOpenAiOptions";
import GeminiLLMView from "./GeminiLLMOptions";
import BedrockLLMView from "./AwsBedrockLLMOptions";
import DeepSeekView from "./DeepSeekOptions";
import CohereAiView from "./CohereAiOptions";
import GroqAiView from "./GroqAiOptions";
import NvidiaNimView from "./NvidiaNimOptions";

import OpenAiLogo from "@/media/llmprovider/openai.png";
import AzureOpenAiLogo from "@/media/llmprovider/azure.png";
import AnthropicLogo from "@/media/llmprovider/anthropic.png";
import OllamaLogo from "@/media/llmprovider/ollama.png";
import LMStudioLogo from "@/media/llmprovider/lmstudio.png";
import LocalAiLogo from "@/media/llmprovider/localai.png";
import TogetherAiLogo from "@/media/llmprovider/togetherai.png";
import FireworksAiLogo from "@/media/llmprovider/fireworksai.jpeg";
import MistralLogo from "@/media/llmprovider/mistral.jpeg";
import HuggingFaceLogo from "@/media/llmprovider/huggingface.png";
import PerplexityLogo from "@/media/llmprovider/perplexity.png";
import OpenRouterLogo from "@/media/llmprovider/openrouter.jpeg";
import GenericOpenAiLogo from "@/media/llmprovider/generic-openai.png";
import GeminiLogo from "@/media/llmprovider/gemini.png";
import BedrockLogo from "@/media/llmprovider/bedrock.png";
import DeepSeekLogo from "@/media/llmprovider/deepseek.png";
import CohereLogo from "@/media/llmprovider/cohere.png";
import GroqLogo from "@/media/llmprovider/groq.png";
import NvidiaLogo from "@/media/llmprovider/nvidia-nim.png";


export const AVAILABLE_LLM_PROVIDERS = [
    {
        name: "OpenAI",
        value: "openai",
        logo: OpenAiLogo,
        options: (settings) => <OpenAIView settings={settings} />,
        description: "The standard for LLM services.",
        requiredConfig: ["OpenAiKey"],
    },
    {
        name: "Azure OpenAI",
        value: "azure",
        logo: AzureOpenAiLogo,
        options: (settings) => <AzureOpenAIView settings={settings} />,
        description: "Enterprise-grade OpenAI models via Azure.",
        requiredConfig: ["AzureOpenAiEndpoint", "AzureOpenAiKey", "AzureOpenAiModelNode"],
    },
    {
        name: "Anthropic",
        value: "anthropic",
        logo: AnthropicLogo,
        options: (settings) => <AnthropicAiView settings={settings} />,
        description: "Claude models by Anthropic.",
        requiredConfig: ["AnthropicApiKey"],
    },
    {
        name: "Ollama",
        value: "ollama",
        logo: OllamaLogo,
        options: (settings) => <OllamaLLMView settings={settings} />,
        description: "Run local LLMs easily.",
        requiredConfig: ["OllamaEndpoint"],
    },
    {
        name: "LM Studio",
        value: "lmstudio",
        logo: LMStudioLogo,
        options: (settings) => <LMStudioView settings={settings} />,
        description: "Local LLM server.",
        requiredConfig: ["LMStudioBasePath"],
    },
    {
        name: "LocalAI",
        value: "localai",
        logo: LocalAiLogo,
        options: (settings) => <LocalAiView settings={settings} />,
        description: "Self-hosted alternative to OpenAI API.",
        requiredConfig: ["LocalAiBasePath"],
    },
    {
        name: "Together AI",
        value: "togetherai",
        logo: TogetherAiLogo,
        options: (settings) => <TogetherAiView settings={settings} />,
        description: "Cloud platform for open-source models.",
        requiredConfig: ["TogetherAiApiKey"],
    },
    {
        name: "Fireworks AI",
        value: "fireworksai",
        logo: FireworksAiLogo,
        options: (settings) => <FireworksAiView settings={settings} />,
        description: "Fast inference for open-source models.",
        requiredConfig: ["FireworksAiApiKey"],
    },
    {
        name: "Mistral",
        value: "mistral",
        logo: MistralLogo,
        options: (settings) => <MistralView settings={settings} />,
        description: "Mistral AI API.",
        requiredConfig: ["MistralApiKey"],
    },
    {
        name: "HuggingFace",
        value: "huggingface",
        logo: HuggingFaceLogo,
        options: (settings) => <HuggingFaceView settings={settings} />,
        description: "Models from HuggingFace Hub.",
        requiredConfig: ["HuggingFaceLLMEndpoint"],
    },
    {
        name: "Perplexity AI",
        value: "perplexity",
        logo: PerplexityLogo,
        options: (settings) => <PerplexityView settings={settings} />,
        description: "Online-enabled LLMs.",
        requiredConfig: ["PerplexityApiKey"],
    },
    {
        name: "OpenRouter",
        value: "openrouter",
        logo: OpenRouterLogo,
        options: (settings) => <OpenRouterView settings={settings} />,
        description: "Unified interface for many LLMs.",
        requiredConfig: ["OpenRouterApiKey"],
    },
    {
        name: "Generic OpenAI",
        value: "generic-openai",
        logo: GenericOpenAiLogo,
        options: (settings) => <NativeLLMView settings={settings} />,
        description: "Connect to any OpenAI-compatible API.",
        requiredConfig: ["GenericOpenAiBasePath", "GenericOpenAiKey"],
    },
    {
        name: "Google Gemini",
        value: "gemini",
        logo: GeminiLogo,
        options: (settings) => <GeminiLLMView settings={settings} />,
        description: "Google's Gemini models.",
        requiredConfig: ["GeminiApiKey"],
    },
    {
        name: "AWS Bedrock",
        value: "bedrock",
        logo: BedrockLogo,
        options: (settings) => <BedrockLLMView settings={settings} />,
        description: "Amazon Bedrock models.",
        requiredConfig: ["AwsBedrockAccessKeyId", "AwsBedrockAccessKeySecret"],
    },
    {
        name: "DeepSeek",
        value: "deepseek",
        logo: DeepSeekLogo,
        options: (settings) => <DeepSeekView settings={settings} />,
        description: "DeepSeek models.",
        requiredConfig: ["DeepSeekApiKey"],
    },
    {
        name: "Cohere",
        value: "cohere",
        logo: CohereLogo,
        options: (settings) => <CohereAiView settings={settings} />,
        description: "Cohere models.",
        requiredConfig: ["CohereApiKeyValue"],
    },
    {
        name: "Groq",
        value: "groq",
        logo: GroqLogo,
        options: (settings) => <GroqAiView settings={settings} />,
        description: "Ultra-fast inference.",
        requiredConfig: ["GroqApiKey"],
    },
    {
        name: "NVIDIA NIM",
        value: "nvidia-nim",
        logo: NvidiaLogo,
        options: (settings) => <NvidiaNimView settings={settings} />,
        description: "NVIDIA microservices.",
        requiredConfig: ["NvidiaNimApiKey"],
    },
];
