import { memo, useRef, useEffect, useState } from "react";
import { Warning } from "@phosphor-icons/react";
import UserIcon from "../../../../UserIcon";
import renderMarkdown from "@/utils/chat/markdown";
import Citations from "../Citation";
import {
  THOUGHT_REGEX_CLOSE,
  THOUGHT_REGEX_COMPLETE,
  THOUGHT_REGEX_OPEN,
  ThoughtChainComponent,
} from "../ThoughtContainer";
import ThoughtAccordion from "@/components/chat/ThoughtAccordion";
import { useGlassBoxSafe } from "@/contexts/GlassBoxContext";
import MeetingCard from "@/components/chat/MeetingCard";
import GraphTrigger from "@/components/chat/GraphTrigger";
import CodeBlockCard from "@/components/chat/CodeBlockCard";

const PromptReply = ({
  uuid,
  reply,
  pending,
  error,
  workspace,
  sources = [],
  closed = true,
}) => {
  const assistantBackgroundColor = "bg-theme-bg-chat";
  const glassBox = useGlassBoxSafe();

  // Track if we should show the new Glass Box UI
  const showGlassBoxUI = glassBox && glassBox.thoughts.length > 0;

  if (!reply && sources.length === 0 && !pending && !error) return null;

  if (pending) {
    return (
      <div
        className={`flex justify-start items-end w-full ${assistantBackgroundColor}`}
      >
        <div className="py-6 px-4 w-full flex gap-x-5 md:max-w-[80%] flex-col">
          <div className="flex gap-x-5">
            <WorkspaceProfileImage workspace={workspace} />
            <div className="flex-1">
              {/* Show ThoughtAccordion while pending if we have thoughts */}
              {showGlassBoxUI ? (
                <ThoughtAccordion
                  steps={glassBox.thoughts}
                  isThinking={glassBox.isThinking}
                  defaultExpanded={true}
                />
              ) : (
                <div className="mt-3 ml-5 dot-falling light:invert"></div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`flex justify-start items-end w-full ${assistantBackgroundColor}`}
      >
        <div className="py-6 px-4 w-full flex gap-x-5 md:max-w-[80%] flex-col">
          <div className="flex gap-x-5">
            <WorkspaceProfileImage workspace={workspace} />
            <span
              className={`inline-block p-2 rounded-lg bg-red-50 text-red-500`}
            >
              <Warning className="h-4 w-4 mb-1 inline-block" /> Could not
              respond to message.
              <span className="text-xs">Reason: {error || "unknown"}</span>
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      key={uuid}
      className={`flex justify-start items-end w-full ${assistantBackgroundColor}`}
    >
      <div className="py-8 px-4 w-full flex gap-x-5 md:max-w-[80%] flex-col">
        <div className="flex gap-x-5">
          <WorkspaceProfileImage workspace={workspace} />
          <div className="flex-1 flex flex-col gap-y-2">
            {/* Show Glass Box ThoughtAccordion if we have thoughts */}
            {showGlassBoxUI && (
              <ThoughtAccordion
                steps={glassBox.thoughts}
                isThinking={false}
                defaultExpanded={false}
              />
            )}

            {/* Render the main content */}
            <RenderAssistantChatContent
              key={`${uuid}-prompt-reply-content`}
              message={reply}
            />

            {/* Render any pending UI triggers from the stream */}
            <StreamUITriggers glassBox={glassBox} />
          </div>
        </div>
        <Citations sources={sources} />
      </div>
    </div>
  );
};

/**
 * Renders UI triggers from the Glass Box context (Meeting, Graph, Code)
 */
function StreamUITriggers({ glassBox }) {
  if (!glassBox) return null;

  return (
    <>
      {glassBox.pendingMeetingRef && (
        <MeetingCard
          id={glassBox.pendingMeetingRef.fileId}
          timestamp={glassBox.pendingMeetingRef.timestamp}
          meeting_meta={glassBox.pendingMeetingRef.meetingMeta}
          onClick={(id, timestamp) => {
            // Re-set the trigger to ensure panel is open (idempotent)
            glassBox.setMeetingRef(glassBox.pendingMeetingRef);
          }}
        />
      )}
      {glassBox.pendingGraphViz && (
        <GraphTrigger
          nodeCount={glassBox.pendingGraphViz.nodes?.length || 0}
          edgeCount={glassBox.pendingGraphViz.edges?.length || 0}
          layerId={glassBox.pendingGraphViz.layerId}
          onClick={() => {
            glassBox.setGraphViz(glassBox.pendingGraphViz);
          }}
        />
      )}
      {glassBox.pendingCodeBlock && (
        <CodeBlockCard
          astData={glassBox.pendingCodeBlock.astData}
          onClick={() => {
            glassBox.setCodeBlock(glassBox.pendingCodeBlock);
          }}
        />
      )}
    </>
  );
}

export function WorkspaceProfileImage({ workspace }) {
  if (!!workspace.pfpUrl) {
    return (
      <div className="relative w-[35px] h-[35px] rounded-full flex-shrink-0 overflow-hidden">
        <img
          src={workspace.pfpUrl}
          alt="Workspace profile picture"
          className="absolute top-0 left-0 w-full h-full object-cover rounded-full bg-white"
        />
      </div>
    );
  }

  return <UserIcon user={{ uid: workspace.slug }} role="assistant" />;
}

function RenderAssistantChatContent({ message }) {
  const contentRef = useRef("");
  const thoughtChainRef = useRef(null);

  useEffect(() => {
    const thinking =
      message.match(THOUGHT_REGEX_OPEN) && !message.match(THOUGHT_REGEX_CLOSE);

    if (thinking && thoughtChainRef.current) {
      thoughtChainRef.current.updateContent(message);
      return;
    }

    const completeThoughtChain = message.match(THOUGHT_REGEX_COMPLETE)?.[0];
    const msgToRender = message.replace(THOUGHT_REGEX_COMPLETE, "");

    if (completeThoughtChain && thoughtChainRef.current) {
      thoughtChainRef.current.updateContent(completeThoughtChain);
    }

    contentRef.current = msgToRender;
  }, [message]);

  const thinking =
    message.match(THOUGHT_REGEX_OPEN) && !message.match(THOUGHT_REGEX_CLOSE);
  if (thinking)
    return (
      <ThoughtChainComponent ref={thoughtChainRef} content="" expanded={true} />
    );

  return (
    <div className="flex flex-col gap-y-1">
      {message.match(THOUGHT_REGEX_COMPLETE) && (
        <ThoughtChainComponent
          ref={thoughtChainRef}
          content=""
          expanded={true}
        />
      )}
      <span
        className="break-words"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(contentRef.current) }}
      />
    </div>
  );
}

export default memo(PromptReply);
