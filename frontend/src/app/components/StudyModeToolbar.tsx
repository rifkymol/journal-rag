"use client";

type ChatMode =
  | "auto"
  | "explain"
  | "summarize"
  | "compare"
  | "quiz"
  | "flashcards"
  | "citations";

type StudyModeToolbarProps = {
  mode: ChatMode;
  language: "auto" | "en" | "id";
  selectedCount: number;
  onModeChange: (mode: ChatMode) => void;
  onLanguageChange: (language: "auto" | "en" | "id") => void;
};

const modes: Array<{ value: ChatMode; label: string }> = [
  { value: "auto", label: "Ask" },
  { value: "explain", label: "Explain" },
  { value: "summarize", label: "Brief" },
  { value: "compare", label: "Compare" },
  { value: "quiz", label: "Quiz me" },
  { value: "flashcards", label: "Flashcards" },
  { value: "citations", label: "Citations" },
];

export function StudyModeToolbar({
  mode,
  language,
  selectedCount,
  onModeChange,
  onLanguageChange,
}: StudyModeToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-[var(--line)] bg-[var(--soft)] px-4 py-3">
      <span className="mr-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        Study mode
      </span>
      <div className="flex flex-wrap gap-1">
        {modes.map((item) => (
          <button
            key={item.value}
            type="button"
            onClick={() => onModeChange(item.value)}
            disabled={item.value === "compare" && selectedCount < 2}
            className={`rounded px-2.5 py-1 text-xs transition ${
              mode === item.value
                ? "bg-[var(--ink)] text-white"
                : "bg-white text-[var(--muted)] hover:text-[var(--ink)]"
            } disabled:cursor-not-allowed disabled:opacity-50`}
          >
            {item.label}
          </button>
        ))}
      </div>
      <select
        value={language}
        onChange={(event) =>
          onLanguageChange(event.target.value as "auto" | "en" | "id")
        }
        className="ml-auto rounded border border-[var(--line)] bg-white px-2 py-1 text-xs text-[var(--muted)] outline-none focus:border-[var(--accent)]"
        aria-label="Response language"
      >
        <option value="auto">Auto language</option>
        <option value="en">English</option>
        <option value="id">Bahasa Indonesia</option>
      </select>
    </div>
  );
}
