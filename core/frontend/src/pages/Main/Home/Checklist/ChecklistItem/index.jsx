import { useState } from "react";
import { CHECKLIST_STORAGE_KEY, CHECKLIST_UPDATED_EVENT } from "../constants";
import { Check } from "@phosphor-icons/react";
import { safeJsonParse } from "@/utils/request";

export function ChecklistItem({ id, title, action, onAction, icon: Icon }) {
  const [isCompleted, setIsCompleted] = useState(() => {
    const stored = window.localStorage.getItem(CHECKLIST_STORAGE_KEY);
    if (!stored) return false;
    const completedItems = safeJsonParse(stored, {});
    return completedItems[id] || false;
  });

  const handleClick = async (e) => {
    e.preventDefault();
    if (!isCompleted) {
      const shouldComplete = await onAction();
      if (shouldComplete) {
        const stored = window.localStorage.getItem(CHECKLIST_STORAGE_KEY);
        const completedItems = safeJsonParse(stored, {});
        completedItems[id] = true;
        window.localStorage.setItem(
          CHECKLIST_STORAGE_KEY,
          JSON.stringify(completedItems)
        );
        setIsCompleted(true);
        window.dispatchEvent(new CustomEvent(CHECKLIST_UPDATED_EVENT));
      }
    } else {
      await onAction();
    }
  };

  return (
    <div
      className={`flex items-center gap-x-4 transition-colors cursor-pointer rounded-lg p-3 group border border-transparent hover:border-ink-action/10 hover:bg-ink-page ${isCompleted
        ? "bg-transparent opacity-60"
        : "bg-white border-ink-border/20 shadow-sm"
        }`}
      onClick={handleClick}
    >
      {Icon && (
        <div className="flex-shrink-0">
          <Icon
            size={18}
            className={
              isCompleted
                ? "text-ink-muted"
                : "text-ink-heading"
            }
          />
        </div>
      )}
      <div className="flex-1">
        <h3
          className={`text-sm font-medium transition-colors duration-200 ${isCompleted
            ? "text-ink-muted line-through decoration-ink-border/50"
            : "text-ink-primary font-semibold"
            }`}
        >
          {title}
        </h3>
      </div>
      {isCompleted ? (
        <div className="w-5 h-5 rounded-full bg-ink-page border border-ink-border flex items-center justify-center">
          <Check
            size={12}
            weight="bold"
            className="text-ink-primary"
          />
        </div>
      ) : (
        <button className="w-[64px] h-[24px] rounded-md bg-ink-action text-white font-bold text-xs transition-all duration-200 flex items-center justify-center hover:opacity-90 shadow-sm">
          {action}
        </button>
      )}
    </div>
  );
}
