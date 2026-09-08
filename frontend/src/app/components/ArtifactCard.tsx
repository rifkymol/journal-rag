"use client";

export type StudyArtifact = {
  type: "summary" | "comparison" | "quiz" | "flashcards" | "citations";
  title: string;
  data: Record<string, unknown>;
};

type ArtifactCardProps = {
  artifact: StudyArtifact;
  onSave: (artifact: StudyArtifact) => void;
};

function renderValue(value: unknown): React.ReactNode {
  if (Array.isArray(value)) {
    return (
      <div className="space-y-2">
        {value.map((item, index) => (
          <div key={index} className="rounded border border-[var(--line)] bg-white p-2">
            {renderValue(item)}
          </div>
        ))}
      </div>
    );
  }

  if (value && typeof value === "object") {
    return (
      <div className="space-y-2">
        {Object.entries(value as Record<string, unknown>).map(([key, item]) => (
          <div key={key}>
            <p className="text-xs font-semibold capitalize text-[var(--muted)]">{key.replaceAll("_", " ")}</p>
            <div className="mt-1 text-sm text-[var(--ink)]">{renderValue(item)}</div>
          </div>
        ))}
      </div>
    );
  }

  return <span>{String(value ?? "Not available")}</span>;
}

export function ArtifactCard({ artifact, onSave }: ArtifactCardProps) {
  return (
    <div className="mt-3 rounded border border-[var(--accent)] bg-[var(--success)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">
            {artifact.type}
          </p>
          <h3 className="mt-1 font-semibold text-[var(--ink)]">{artifact.title}</h3>
        </div>
        <button
          type="button"
          onClick={() => onSave(artifact)}
          className="rounded border border-[var(--line)] bg-white px-2.5 py-1 text-xs text-[var(--muted)] hover:text-[var(--ink)]"
        >
          Save note
        </button>
      </div>
      <div className="mt-3">{renderValue(artifact.data)}</div>
    </div>
  );
}
