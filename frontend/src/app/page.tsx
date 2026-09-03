"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  FileText,
  Loader2,
  RefreshCw,
  Send,
  Trash2,
  Upload,
  User,
} from "lucide-react";

type Journal = {
  document_id: string;
  filename: string;
  pages: number;
  chunks: number;
};

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceReference[];
};

type SourceReference = {
  source: string;
  pages: number[];
  page_label: string;
};

const starterMessages: Message[] = [
  {
    id: "welcome",
    role: "assistant",
    content: "Select a journal and ask a question about it.",
  },
];

const MAX_JOURNALS = 3;

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

function createSessionId() {
  if (typeof window === "undefined") {
    return "";
  }

  const storedSessionId = window.localStorage.getItem("journal-session-id");

  if (storedSessionId) {
    return storedSessionId;
  }

  const nextSessionId = createId();

  window.localStorage.setItem("journal-session-id", nextSessionId);
  return nextSessionId;
}

async function readApiError(response: Response, fallback: string) {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    const data = await response.json().catch(() => null);
    return typeof data?.detail === "string" ? data.detail : fallback;
  }

  const text = await response.text().catch(() => "");
  return text || fallback;
}

function normalizeSources(value: unknown): SourceReference[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }

      const sourceItem = item as Partial<SourceReference>;
      if (
        typeof sourceItem.source !== "string" ||
        typeof sourceItem.page_label !== "string" ||
        !Array.isArray(sourceItem.pages)
      ) {
        return null;
      }

      return {
        source: sourceItem.source,
        pages: sourceItem.pages.filter(
          (page): page is number => typeof page === "number",
        ),
        page_label: sourceItem.page_label,
      };
    })
    .filter((item): item is SourceReference => item !== null);
}

function formatSourcePages(source: SourceReference) {
  if (!source.page_label) {
    return "Pages unavailable";
  }

  return `${source.pages.length === 1 ? "p." : "pp."} ${source.page_label}`;
}

export default function Home() {
  const [journals, setJournals] = useState<Journal[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [messages, setMessages] = useState<Message[]>(starterMessages);
  const [message, setMessage] = useState("");
  const [threadId, setThreadId] = useState(() => createThreadId());
  const [isLoadingJournals, setIsLoadingJournals] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [deletingId, setDeletingId] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const selectedJournal = useMemo(
    () =>
      journals.find((journal) => journal.document_id === selectedDocumentId) ??
      null,
    [journals, selectedDocumentId],
  );

  const hasReachedJournalLimit = journals.length >= MAX_JOURNALS;

  useEffect(() => {
    setSessionId(
      createSessionId()
    );
  }, []);

  const canSend = message.trim().length > 0 && Boolean(sessionId) && !isSending;

  useEffect(() => {
    if (!sessionId) {
      return;
    }
    void loadJournals();
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  async function loadJournals() {
    setIsLoadingJournals(true);
    setError("");

    try {
      const response = await fetch("/journals",{
        headers: {
          "X-Session-ID": sessionId,
        },
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, "Unable to load journals."));
      }

      const data = await response.json();
      const nextJournals: Journal[] = Array.isArray(data?.journals)
        ? data.journals
        : [];

      setJournals(nextJournals);
      setSelectedDocumentId((current) => {
        if (nextJournals.some((journal) => journal.document_id === current)) {
          return current;
        }

        return nextJournals[0]?.document_id ?? "";
      });
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to load journals.",
      );
    } finally {
      setIsLoadingJournals(false);
    }
  }

  async function handleUpload(file: File) {
    if (!sessionId) {
      setError("Session is still loading. Please try again.");
      return;
    }

    if (hasReachedJournalLimit) {
      setError("You can upload a maximum of 3 PDFs. Delete one PDF before uploading another.");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    if (file.type !== "application/pdf") {
      setError("Only PDF files are allowed.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setIsUploading(true);
    setError("");

    try {
      const response = await fetch("/journals", {
        method: "POST",
        headers: {
          "X-Session-ID": sessionId,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, "Unable to upload journal."));
      }

      const uploadedJournal: Journal = await response.json();
      setJournals((current) => [
        uploadedJournal,
        ...current.filter(
          (journal) => journal.document_id !== uploadedJournal.document_id,
        ),
      ]);
      setSelectedDocumentId(uploadedJournal.document_id);
      resetConversation();
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to upload journal.",
      );
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  async function handleDelete(journal: Journal) {
    if (!sessionId) {
      setError("Session is still loading. Please try again.");
      return;
    }

    const confirmed = window.confirm(`Delete ${journal.filename}?`);
    if (!confirmed) {
      return;
    }

    setDeletingId(journal.document_id);
    setError("");

    try {
      const response = await fetch(`/journals/${journal.document_id}`, {
        method: "DELETE",
        headers: {
          "X-Session-ID": sessionId,
        },
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, "Unable to delete journal."));
      }

      setJournals((current) => {
        const nextJournals = current.filter(
          (item) => item.document_id !== journal.document_id,
        );

        if (selectedDocumentId === journal.document_id) {
          setSelectedDocumentId(nextJournals[0]?.document_id ?? "");
          resetConversation();
        }

        return nextJournals;
      });
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to delete journal.",
      );
    } finally {
      setDeletingId("");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const userText = message.trim();
    if (!userText || isSending) {
      return;
    }

    if (!sessionId) {
      setError("Session is still loading. Please try again.");
      return;
    }

    const currentThreadId = threadId || createThreadId();
    setThreadId(currentThreadId);

    const userMessage: Message = {
      id: createId(),
      role: "user",
      content: userText,
    };
    const assistantMessageId = createId();

    setMessages((current) => [
      ...current,
      userMessage,
      {
        id: assistantMessageId,
        role: "assistant",
        content: "",
      },
    ]);
    setMessage("");
    setError("");
    setIsSending(true);

    try {
      const response = await fetch("/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId,
        },
        body: JSON.stringify({
          message: userText,
          thread_id: currentThreadId,
          document_id: selectedDocumentId,
        }),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, "The chat API returned an error."));
      }

      if (!response.body) {
        throw new Error("The chat API did not return a stream.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let assistantText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        let boundaryMatch = buffer.match(/\r?\n\r?\n/);
        while (boundaryMatch?.index !== undefined) {
          const boundaryIndex = boundaryMatch.index;
          const eventBlock = buffer.slice(0, boundaryIndex);
          buffer = buffer.slice(boundaryIndex + boundaryMatch[0].length);
          const eventName =
            eventBlock
              .split(/\r?\n/)
              .find((line) => line.startsWith("event:"))
              ?.slice(6)
              .trim() ?? "message";

          const data = eventBlock
            .split(/\r?\n/)
            .filter((line) => line.startsWith("data:"))
            .map((line) => {
              const value = line.slice(5);
              return value.startsWith(" ") ? value.slice(1) : value;
            })
            .join("\n");

          if (eventName === "sources" && data) {
            try {
              const nextSources = normalizeSources(
                JSON.parse(data)
              );

              setMessages((current) =>
                current.map((item) =>
                  item.id === assistantMessageId
                    ? { ...item, sources: nextSources }
                    : item,
                ),
              );
            } catch {
              // Ignore malformed source metadata; the streamed answer is still useful.
            }
          }

          if (eventName === "message" && data && data !== "[DONE]") {
            assistantText += data;
            setMessages((current) =>
              current.map((item) =>
                item.id === assistantMessageId
                  ? { ...item, content: assistantText }
                  : item,
              ),
            );
          }

          boundaryMatch = buffer.match(/\r?\n\r?\n/);
        }
      }

      if (!assistantText) {
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantMessageId
              ? { ...item, content: "No answer was returned." }
              : item,
          ),
        );
      }
    } catch (caughtError) {
      setMessages((current) =>
        current.filter((item) => item.id !== assistantMessageId),
      );
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to reach /chat.",
      );
    } finally {
      setIsSending(false);
    }
  }

  function resetConversation() {
    const nextThreadId = createId();
    window.localStorage.setItem("journal-chat-thread-id", nextThreadId);
    setThreadId(nextThreadId);
    setMessages(starterMessages);
    setMessage("");
    setError("");
  }

  return (
    <main className="grid h-screen overflow-hidden bg-[var(--surface)] text-[var(--ink)] md:grid-cols-[320px_1fr]">
      <aside className="flex min-h-0 flex-col border-b border-[var(--line)] bg-white md:border-b-0 md:border-r">
        <header className="flex shrink-0 items-center justify-between border-b border-[var(--line)] px-4 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-normal text-[var(--muted)]">
              Journals
            </p>
            <h1 className="mt-1 text-xl font-semibold">Journal RAG</h1>
          </div>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading || hasReachedJournalLimit || !sessionId}
            className="flex h-10 w-10 items-center justify-center rounded border border-[var(--line)] bg-white text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--ink)] disabled:cursor-not-allowed disabled:opacity-60"
            aria-label="Upload journal"
            title={
              hasReachedJournalLimit
                ? "Upload limit reached"
                : "Upload journal"
            }
          >
            {isUploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                void handleUpload(file);
              }
            }}
          />
        </header>

        <div className="flex shrink-0 items-center justify-between border-b border-[var(--line)] px-4 py-3">
          <span className="text-sm text-[var(--muted)]">
            {journals.length}/{MAX_JOURNALS}{" "}
            {journals.length === 1 ? "journal" : "journals"}
          </span>
          <button
            type="button"
            onClick={() => void loadJournals()}
            disabled={isLoadingJournals}
            className="flex h-9 w-9 items-center justify-center rounded border border-[var(--line)] bg-white text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--ink)] disabled:cursor-not-allowed disabled:opacity-60"
            aria-label="Refresh journals"
            title="Refresh journals"
          >
            <RefreshCw
              className={`h-4 w-4 ${isLoadingJournals ? "animate-spin" : ""}`}
            />
          </button>
        </div>

        {hasReachedJournalLimit && (
          <div className="border-b border-[var(--warning-line)] bg-[var(--warning)] px-4 py-3 text-sm text-[var(--warning-ink)]">
            Upload limit reached. Delete one PDF before uploading another.
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          {isLoadingJournals && journals.length === 0 ? (
            <div className="flex items-center gap-2 px-2 py-3 text-sm text-[var(--muted)]">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading journals...
            </div>
          ) : journals.length === 0 ? (
            <div className="border border-dashed border-[var(--line)] bg-[var(--soft)] px-4 py-5 text-sm text-[var(--muted)]">
              Upload a PDF journal to start.
            </div>
          ) : (
            <div className="space-y-2">
              {journals.map((journal) => {
                const isSelected = selectedDocumentId === journal.document_id;
                const isDeleting = deletingId === journal.document_id;

                return (
                  <article
                    key={journal.document_id}
                    className={`grid grid-cols-[1fr_auto] gap-2 rounded border p-3 transition ${
                      isSelected
                        ? "border-[var(--accent)] bg-[var(--success)]"
                        : "border-[var(--line)] bg-white hover:border-[var(--accent)]"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedDocumentId(journal.document_id);
                        resetConversation();
                      }}
                      className="min-w-0 text-left"
                    >
                      <span className="flex items-center gap-2 text-sm font-medium">
                        <FileText className="h-4 w-4 shrink-0 text-[var(--accent)]" />
                        <span className="truncate">{journal.filename}</span>
                      </span>
                      <span className="mt-2 block text-xs text-[var(--muted)]">
                        {journal.pages} pages · {journal.chunks} chunks
                      </span>
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDelete(journal)}
                      disabled={isDeleting}
                      className="flex h-9 w-9 items-center justify-center rounded text-[var(--muted)] transition hover:bg-[var(--warning)] hover:text-[var(--warning-ink)] disabled:cursor-not-allowed disabled:opacity-60"
                      aria-label={`Delete ${journal.filename}`}
                      title="Delete journal"
                    >
                      {isDeleting ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </aside>

      <section className="flex min-h-0 flex-col">
        <header className="flex shrink-0 items-center justify-between border-b border-[var(--line)] bg-white px-4 py-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-normal text-[var(--muted)]">
              Chat
            </p>
            <h2 className="mt-1 truncate text-xl font-semibold">
              {selectedJournal?.filename ?? "No journal selected"}
            </h2>
          </div>
          <button
            type="button"
            onClick={resetConversation}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded border border-[var(--line)] bg-white text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--ink)]"
            aria-label="Reset conversation"
            title="Reset conversation"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-5">
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
                {item.content ? (
                  <>
                    <p className="whitespace-pre-wrap break-words">
                      {item.content}
                    </p>

                    {item.role === "assistant" && item.sources?.length ? (
                      <div className="mt-3 border-t border-[var(--line)] pt-3">
                        <p className="text-xs font-semibold uppercase tracking-normal text-[var(--muted)]">
                          Sources
                        </p>
                        <div className="mt-2 space-y-2">
                          {item.sources.map((source) => (
                            <div
                              key={`${source.source}-${source.page_label}`}
                              className="rounded border border-[var(--line)] bg-[var(--soft)] px-3 py-2"
                            >
                              <p className="break-words text-xs font-medium text-[var(--ink)]">
                                {source.source}
                              </p>
                              <p className="mt-1 text-xs text-[var(--muted)]">
                                {formatSourcePages(source)}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </>
                ) : (
                  <Loader2 className="h-4 w-4 animate-spin text-[var(--muted)]" />
                )}
              </div>

              {item.role === "user" && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--ink)] text-white">
                  <User className="h-4 w-4" />
                </div>
              )}
            </article>
          ))}

          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div className="mx-4 mb-3 rounded border border-[var(--warning-line)] bg-[var(--warning)] px-4 py-3 text-sm text-[var(--warning-ink)]">
            {error}
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="shrink-0 border-t border-[var(--line)] bg-white px-4 py-4"
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
              placeholder={
                selectedDocumentId
                  ? "Ask about the selected journal..."
                  : "Ask for related scholarly references..."
              }
              rows={1}
              disabled={isSending}
              className="max-h-32 min-h-12 flex-1 resize-none rounded border border-[var(--line)] bg-white px-3 py-3 text-sm leading-5 outline-none transition focus:border-[var(--accent)] disabled:cursor-not-allowed disabled:bg-[var(--soft)]"
            />
            <button
              type="submit"
              disabled={!canSend}
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded bg-[var(--accent)] text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:bg-[var(--line)]"
              aria-label="Send message"
              title="Send message"
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
