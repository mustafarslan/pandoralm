import React from "react";
import UserIcon from "../UserIcon";
import { userFromStorage } from "@/utils/request";
import renderMarkdown from "@/utils/chat/markdown";
import DOMPurify from "@/utils/chat/purify";

export default function ChatBubble({ message, type, popMsg }) {
  const isUser = type === "user";

  return (
    <div
      className={`flex justify-center items-end w-full bg-transparent`}
    >
      <div className={`py-8 px-4 w-full flex gap-x-5 md:max-w-[80%] flex-col`}>
        <div className="flex gap-x-5">
          <UserIcon
            user={{ uid: isUser ? userFromStorage()?.username : "system" }}
            role={type}
          />

          <div
            className={`markdown whitespace-pre-line font-normal text-sm md:text-sm flex flex-col gap-y-1 mt-2 ${isUser ? 'bg-white/10 text-pandora-text backdrop-blur-sm border border-white/5 rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm' : 'text-[var(--ink-body)]'}`}
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(renderMarkdown(message)),
            }}
          />
        </div>
      </div>
    </div>
  );
}
