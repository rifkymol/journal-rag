"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Bot, Loader2, RefreshCw, Send, User } from "lucide-react";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

const starterMessages: Message[] = [
  {
    id: "welcome",
    role: "assistant",
    content: "Hi, ask me anything.",
  },
];

function createId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `id-${Date.now()}`;
}

function createThreadId() {
  if (typeof window === "undefined") {
    return "";
  }

  const storedThreadId = window.localStorage.getItem("journal-chat-thread-id");
  if (storedThreadId) {
    return storedThreadId;
  }

  const nextThreadId = createId();
  window.localStorage.setItem("journal-chat-thread-id", nextThreadId);
  return nextThreadId;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>(starterMessages);
  const [message, setMessage] = useState("");
  const [threadId, setThreadId] = useState(() => createThreadId());
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const canSend = message.trim().length > 0 && !isSending;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const userText = message.trim();
    if (!userText || isSending) {
      return;
    }

    const currentThreadId = threadId || createThreadId();
    setThreadId(currentThreadId);

    const userMessage: Message = {
      id: createId(),
      role: "user",
      content: userText,
    };

    setMessages((current) => [...current, userMessage]);
    setMessage("");
    setError("");
    setIsSending(true);

    try {
      const response = await fetch("/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userText,
          thread_id: currentThreadId,
        }),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const detail =
          typeof data?.detail === "string"
            ? data.detail
            : "The chat API returned an error.";
        throw new Error(detail);
      }

      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: data?.answer ?? "No answer was returned.",
        },
      ]);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to reach /chat.",
      );
    } finally {
      setIsSending(false);
    }
  }

  function clearConversation() {
    const nextThreadId = createId();
    window.localStorage.setItem("journal-chat-thread-id", nextThreadId);
    setThreadId(nextThreadId);
    setMessages(starterMessages);
    setMessage("");
    setError("");
  }

  return (
    <main className="flex h-screen overflow-hidden bg-[var(--surface)] text-[var(--ink)]">
      <section className="mx-auto flex h-full w-full max-w-3xl flex-col px-4 py-5">
        <header className="flex shrink-0 items-center justify-between border-b border-[var(--line)] pb-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-normal text-[var(--muted)]">
              Using /chat
            </p>
            <h1 className="mt-1 text-2xl font-semibold">Journal Chat</h1>
          </div>
          <button
            type="button"
            onClick={clearConversation}
            className="flex h-10 w-10 items-center justify-center rounded border border-[var(--line)] bg-white text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--ink)]"
            aria-label="Reset conversation"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto py-5">
          {messages.map((item) => (
            <article
              key={item.id}
              className={`flex gap-3 ${
                item.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {item.role === "assistant" && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--soft)] text-[var(--accent)]">
                  <Bot className="h-4 w-4" />
                </div>
              )}

              <div
                className={`max-w-[82%] rounded-md px-4 py-3 text-sm leading-6 ${
                  item.role === "user"
                    ? "bg-[var(--ink)] text-white"
                    : "border border-[var(--line)] bg-white"
                }`}
              >
                <p className="whitespace-pre-wrap break-words">
                  {item.content}
                </p>
              </div>

              {item.role === "user" && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--ink)] text-white">
                  <User className="h-4 w-4" />
                </div>
              )}
            </article>
          ))}

          {isSending && (
            <div className="flex items-center gap-3 text-sm text-[var(--muted)]">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--soft)] text-[var(--accent)]">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
              Thinking...
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div className="mb-3 rounded border border-[var(--warning-line)] bg-[var(--warning)] px-4 py-3 text-sm text-[var(--warning-ink)]">
            {error}
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="shrink-0 border-t border-[var(--line)] pt-4"
        >
          <div className="flex gap-3">
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              placeholder="Type a message..."
              rows={1}
              className="max-h-32 min-h-12 flex-1 resize-none rounded border border-[var(--line)] bg-white px-3 py-3 text-sm leading-5 outline-none transition focus:border-[var(--accent)]"
            />
            <button
              type="submit"
              disabled={!canSend}
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded bg-[var(--accent)] text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:bg-[var(--line)]"
              aria-label="Send message"
            >
              {isSending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
