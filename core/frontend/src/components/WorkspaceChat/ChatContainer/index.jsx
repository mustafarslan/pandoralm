import { useState, useEffect, useContext } from "react";
import ChatHistory from "./ChatHistory";
import { CLEAR_ATTACHMENTS_EVENT, DndUploaderContext } from "./DnDWrapper";
import PromptInput, {
  PROMPT_INPUT_EVENT,
  PROMPT_INPUT_ID,
} from "./PromptInput";
import Workspace from "@/models/workspace";
import handleChat, { ABORT_STREAM_EVENT } from "@/utils/chat";
import { isMobile } from "react-device-detect";
import { useParams } from "react-router-dom";
import { v4 } from "uuid";
import handleSocketResponse, {
  websocketURI,
  AGENT_SESSION_END,
  AGENT_SESSION_START,
} from "@/utils/chat/agent";
import DnDFileUploaderWrapper from "./DnDWrapper";
import SpeechRecognition, {
  useSpeechRecognition,
} from "react-speech-recognition";
import { ChatTooltips } from "./ChatTooltips";
import { MetricsProvider } from "./ChatHistory/HistoricalMessage/Actions/RenderMetrics";


export default function ChatContainer({ workspace, knownHistory = [] }) {
  const { threadSlug = null } = useParams();
  const [message, setMessage] = useState("");
  const [loadingResponse, setLoadingResponse] = useState(false);
  const [chatHistory, setChatHistory] = useState(knownHistory);
  const [socketId, setSocketId] = useState(null);
  const [websocket, setWebsocket] = useState(null);
  const [chatMode, setChatMode] = useState("auto");
  const { files, parseAttachments } = useContext(DndUploaderContext);

  // Maintain state of message from whatever is in PromptInput
  const handleMessageChange = (event) => {
    setMessage(event.target.value);
  };

  const { listening, resetTranscript } = useSpeechRecognition({
    clearTranscriptOnListen: true,
  });

  /**
   * Emit an update to the state of the prompt input without directly
   * passing a prop in so that it does not re-render constantly.
   * @param {string} messageContent - The message content to set
   * @param {'replace' | 'append'} writeMode - Replace current text or append to existing text (default: replace)
   */
  function setMessageEmit(messageContent = "", writeMode = "replace") {
    if (writeMode === "append") setMessage((prev) => prev + messageContent);
    else setMessage(messageContent ?? "");

    // Push the update to the PromptInput component (same logic as above to keep in sync)
    window.dispatchEvent(
      new CustomEvent(PROMPT_INPUT_EVENT, {
        detail: { messageContent, writeMode },
      })
    );
  }

  const sendCommand = async ({
    text,
    autoSubmit = false,
    history = null,
    attachments = [],
  }) => {
    if (!autoSubmit) {
      setMessageEmit(text);
      return;
    }

    if (history) {
      const newHistory = [
        ...history,
        {
          content: "",
          role: "assistant",
          pending: true,
          userMessage: text,
          animate: true,
        },
      ];
      setChatHistory(newHistory);
      setMessageEmit("");
      setLoadingResponse(true);
    } else {
      const prevChatHistory = [
        ...chatHistory,
        {
          content: text,
          role: "user",
          attachments: parseAttachments(),
          mode: chatMode,
        },
        {
          content: "",
          role: "assistant",
          pending: true,
          userMessage: text,
          animate: true,
        },
      ];
      setChatHistory(prevChatHistory);
      setMessageEmit("");
      setLoadingResponse(true);
    }
  };

  const regenerateAssistantMessage = () => {
    const prevHistory = chatHistory.slice(0, -1);
    const lastUserResult = prevHistory[prevHistory.length - 1];
    if (!lastUserResult || lastUserResult.role !== "user") return;

    const newHistory = [
      ...prevHistory,
      {
        content: "",
        role: "assistant",
        pending: true,
        userMessage: lastUserResult.content,
        animate: true,
      },
    ];
    setChatHistory(newHistory);
    setLoadingResponse(true);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!message || message === "") return false;
    const prevChatHistory = [
      ...chatHistory,
      {
        content: message,
        role: "user",
        attachments: parseAttachments(),
        mode: chatMode, // Snapshot mode for this message
      },
      {
        content: "",
        role: "assistant",
        pending: true,
        userMessage: message,
        animate: true,
      },
    ];

    if (listening) {
      // Stop the mic if the send button is clicked
      endSTTSession();
    }
    setChatHistory(prevChatHistory);
    setMessageEmit("");
    setLoadingResponse(true);
  };

  // ... (keeping existing code) ...

  useEffect(() => {
    async function fetchReply() {
      const promptMessage =
        chatHistory.length > 0 ? chatHistory[chatHistory.length - 1] : null;
      const remHistory = chatHistory.length > 0 ? chatHistory.slice(0, -1) : [];
      var _chatHistory = [...remHistory];

      // Override hook for new messages to now go to agents until the connection closes
      if (!!websocket) {
        if (!promptMessage || !promptMessage?.userMessage) return false;
        window.dispatchEvent(new CustomEvent(CLEAR_ATTACHMENTS_EVENT));
        websocket.send(
          JSON.stringify({
            type: "awaitingFeedback",
            feedback: promptMessage?.userMessage,
          })
        );
        return;
      }

      if (!promptMessage || !promptMessage?.userMessage) return false;

      // If running and edit or regeneration, this history will already have attachments
      // so no need to parse the current state.
      const attachments = promptMessage?.attachments ?? parseAttachments();
      // Use the mode from the message if available (historic), otherwise current state
      // Actually strictly use the last user message's mode if we stored it
      const prevUserMsg = chatHistory.length >= 2 ? chatHistory[chatHistory.length - 2] : null;
      const requestMode = prevUserMsg?.mode || chatMode;

      window.dispatchEvent(new CustomEvent(CLEAR_ATTACHMENTS_EVENT));

      try {
        await Workspace.multiplexStream({
          workspaceSlug: workspace.slug,
          threadSlug,
          prompt: promptMessage.userMessage,
          chatHandler: (chatResult) =>
            handleChat(
              chatResult,
              setLoadingResponse,
              setChatHistory,
              remHistory,
              _chatHistory,
              setSocketId
            ),
          attachments,
          mode: requestMode,
        });
      } finally {
        setLoadingResponse(false);
      }
      return;
    }
    loadingResponse === true && fetchReply();
  }, [loadingResponse, chatHistory, workspace]);

  // ...

  return (
    <div
      style={{ height: isMobile ? "100%" : "calc(100% - 32px)" }}
      className="transition-all duration-500 relative md:ml-[2px] md:mr-[16px] md:my-[16px] md:rounded-[16px] bg-os-bg w-full h-full flex-1 flex flex-col overflow-hidden z-[2]"
    >
      {isMobile && <div className="h-8 w-full bg-os-bg shrink-0" />}
      <DnDFileUploaderWrapper>
        <MetricsProvider>
          <ChatHistory
            history={chatHistory}
            workspace={workspace}
            sendCommand={sendCommand}
            updateHistory={setChatHistory}
            regenerateAssistantMessage={regenerateAssistantMessage}
            hasAttachments={files.length > 0}
          />
        </MetricsProvider>
        <PromptInput
          submit={handleSubmit}
          onChange={handleMessageChange}
          isStreaming={loadingResponse}
          sendCommand={sendCommand}
          attachments={files}
          chatMode={chatMode}
          setChatMode={setChatMode}
        />
      </DnDFileUploaderWrapper>
      <ChatTooltips />
    </div>
  );
}
