"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
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
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node || typeof node.scrollTo !== "function") return;
    node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [messages.length, isSending]);

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
    <aside className="relative flex max-h-[min(720px,calc(100vh-96px))] min-h-[420px] flex-col overflow-hidden rounded-3xl border border-[var(--stroke)] surface-glass shadow-[var(--shadow)] lg:sticky lg:top-24 lg:min-h-[560px]">
      <span
        aria-hidden
        className="pointer-events-none absolute -right-16 -top-16 h-44 w-44 rounded-full opacity-50 blur-3xl"
        style={{
          background:
            "radial-gradient(circle, rgba(132,160,176,0.32), transparent 70%)",
        }}
      />
      <span
        aria-hidden
        className="pointer-events-none absolute -bottom-16 -left-16 h-44 w-44 rounded-full opacity-50 blur-3xl"
        style={{
          background:
            "radial-gradient(circle, rgba(72,112,144,0.28), transparent 70%)",
        }}
      />

      <div className="relative border-b border-[var(--stroke)] px-5 pb-4 pt-5">
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-white shadow-[0_8px_18px_rgba(132,160,176,0.30)]"
            style={{
              background:
                "linear-gradient(135deg, var(--pacific-blue) 0%, var(--aqua-mist) 100%)",
            }}
          >
            <span className="font-display text-sm font-bold tracking-wide">AI</span>
          </span>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.32em] text-[var(--slate)]">
              Assistant
            </p>
            <h2 className="font-display text-xl font-semibold text-[var(--deep-sea)]">
              Board Assistant
            </h2>
          </div>
          {isSending && (
            <span
              aria-hidden
              className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-[var(--surface-muted)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--pacific-blue)]"
            >
              <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-[var(--pacific-blue)]" />
              live
            </span>
          )}
        </div>
      </div>

      <div
        ref={scrollRef}
        className="scroll-soft relative flex flex-1 flex-col gap-3 overflow-y-auto px-5 py-4"
      >
        {messages.length === 0 ? (
          <div className="flex flex-1 flex-col items-stretch justify-center gap-3 rounded-2xl border border-dashed border-[var(--stroke)] bg-white/60 p-5 text-center">
            <p className="text-sm font-semibold text-[var(--deep-sea)]">
              Ready when you are.
            </p>
            <p className="text-xs leading-5 text-[var(--slate)]">
              Ask the assistant to add cards, move work between columns, or rename a stage.
            </p>
            <div className="flex flex-wrap justify-center gap-2 pt-1">
              {[
                "Add a launch notes card",
                "Move QA tasks to Review",
                "Rename Backlog to Inbox",
              ].map((hint) => (
                <button
                  key={hint}
                  type="button"
                  onClick={() => setMessage(hint)}
                  className="focus-ring rounded-full border border-[var(--stroke)] bg-white/80 px-3 py-1.5 text-[11px] font-semibold text-[var(--deep-sea)] transition hover:border-[var(--pacific-blue)] hover:text-[var(--pacific-blue)]"
                >
                  {hint}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((item, index) => (
            <div
              key={`${item.role}-${index}-${item.content.slice(0, 12)}`}
              className={
                item.role === "user"
                  ? "ml-6 break-words rounded-2xl rounded-br-md px-4 py-3 text-sm leading-6 text-white shadow-[0_8px_18px_rgba(72,112,144,0.28)]"
                  : "mr-6 break-words rounded-2xl rounded-bl-md border border-[var(--stroke)] bg-white/90 px-4 py-3 text-sm leading-6 text-[var(--deep-sea)] shadow-[0_4px_12px_rgba(31,48,85,0.05)]"
              }
              style={
                item.role === "user"
                  ? {
                      background:
                        "linear-gradient(135deg, var(--pacific-blue) 0%, var(--aqua-mist) 100%)",
                    }
                  : undefined
              }
            >
              {item.content}
            </div>
          ))
        )}
        {isSending && (
          <div className="mr-6 flex items-center gap-2 rounded-2xl rounded-bl-md border border-[var(--stroke)] bg-white/90 px-4 py-3 text-sm font-semibold text-[var(--slate)]">
            <span className="pulse-dot inline-block h-1.5 w-1.5 rounded-full bg-[var(--pacific-blue)]" />
            <span
              className="pulse-dot inline-block h-1.5 w-1.5 rounded-full bg-[var(--aqua-mist)]"
              style={{ animationDelay: "0.2s" }}
            />
            <span
              className="pulse-dot inline-block h-1.5 w-1.5 rounded-full bg-[var(--coral-sunset)]"
              style={{ animationDelay: "0.4s" }}
            />
            <span className="ml-1 text-xs uppercase tracking-[0.2em]">Thinking...</span>
          </div>
        )}
      </div>

      {error && (
        <p className="relative mx-5 mb-3 break-words rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
          {error}
        </p>
      )}

      <form
        className="relative flex flex-col gap-3 border-t border-[var(--stroke)] bg-white/70 px-5 py-4"
        onSubmit={handleSubmit}
      >
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
          className="focus-ring scroll-soft min-h-24 resize-none rounded-2xl border border-[var(--stroke)] bg-white/90 px-4 py-3 text-sm leading-6 text-[var(--deep-sea)] outline-none placeholder:text-[var(--slate)]"
          placeholder="Create a launch notes card"
        />
        <div className="flex items-center justify-between gap-3">
          <p
            className="text-xs font-semibold tabular-nums text-[var(--slate)]"
            data-testid="ai-message-counter"
          >
            {message.length}/{MESSAGE_MAX_LENGTH}
          </p>
          <button
            type="submit"
            disabled={isSending || !message.trim()}
            className="focus-ring rounded-2xl px-5 py-3 text-sm font-semibold uppercase tracking-[0.16em] text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
            style={{
              background:
                "linear-gradient(135deg, var(--pacific-blue) 0%, var(--aqua-mist) 100%)",
              boxShadow: "0 12px 26px rgba(132, 160, 176, 0.28)",
            }}
          >
            Send
          </button>
        </div>
      </form>
    </aside>
  );
};
