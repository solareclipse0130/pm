"use client";

import { FormEvent, useState } from "react";
import type { ChatMessage } from "@/lib/aiApi";

const MESSAGE_MAX_LENGTH = 2000;

type AiChatSidebarProps = {
  messages: ChatMessage[];
  isSending: boolean;
  error: string;
  onSend: (message: string) => Promise<void>;
};

export const AiChatSidebar = ({
  messages,
  isSending,
  error,
  onSend,
}: AiChatSidebarProps) => {
  const [message, setMessage] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || isSending) {
      return;
    }
    setMessage("");
    await onSend(trimmed);
  };

  return (
    <aside className="flex max-h-[min(720px,calc(100vh-96px))] min-h-[420px] flex-col rounded-3xl border border-[var(--stroke)] bg-white p-4 shadow-[var(--shadow)] lg:sticky lg:top-24 lg:min-h-[520px]">
      <div className="border-b border-[var(--stroke)] pb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--gray-text)]">
          AI
        </p>
        <h2 className="mt-2 font-display text-xl font-semibold text-[var(--navy-dark)]">
          Board Assistant
        </h2>
      </div>

      <div className="mt-4 flex flex-1 flex-col gap-3 overflow-y-auto pr-1">
        {messages.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-[var(--stroke)] px-4 py-5 text-sm font-semibold text-[var(--gray-text)]">
            No messages yet.
          </p>
        ) : (
          messages.map((item, index) => (
            <div
              key={`${item.role}-${index}-${item.content.slice(0, 12)}`}
              className={
                item.role === "user"
                  ? "ml-6 break-words rounded-2xl bg-[var(--primary-blue)] px-4 py-3 text-sm leading-6 text-white"
                  : "mr-6 break-words rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm leading-6 text-[var(--navy-dark)]"
              }
            >
              {item.content}
            </div>
          ))
        )}
        {isSending && (
          <p className="mr-6 rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm font-semibold text-[var(--gray-text)]">
            Thinking...
          </p>
        )}
      </div>

      {error && (
        <p className="mt-4 break-words rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
          {error}
        </p>
      )}

      <form className="mt-4 flex flex-col gap-3" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="ai-message">
          Message
        </label>
        <textarea
          id="ai-message"
          value={message}
          onChange={(event) =>
            setMessage(event.target.value.slice(0, MESSAGE_MAX_LENGTH))
          }
          maxLength={MESSAGE_MAX_LENGTH}
          className="min-h-24 resize-none rounded-2xl border border-[var(--stroke)] px-4 py-3 text-sm leading-6 text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
          placeholder="Create a launch notes card"
        />
        <div className="flex items-center justify-between gap-3">
          <p
            className="text-xs font-semibold text-[var(--gray-text)]"
            data-testid="ai-message-counter"
          >
            {message.length}/{MESSAGE_MAX_LENGTH}
          </p>
          <button
            type="submit"
            disabled={isSending || !message.trim()}
            className="rounded-2xl bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </form>
    </aside>
  );
};
