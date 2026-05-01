import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  isHighlighted?: boolean;
  onUpdate: (cardId: string, title: string, details: string) => void;
  onDelete: (cardId: string) => void;
};

export const KanbanCard = ({
  card,
  isHighlighted = false,
  onUpdate,
  onDelete,
}: KanbanCardProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details);
  const [titleError, setTitleError] = useState("");
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const exitEdit = () => {
    setTitle(card.title);
    setDetails(card.details);
    setTitleError("");
    setIsEditing(false);
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "group/card relative rounded-2xl border bg-white px-4 py-4 shadow-[0_8px_18px_rgba(15,42,71,0.06)]",
        "border-[var(--stroke)] transition-all duration-200",
        !isDragging && !isEditing && "hover:-translate-y-0.5 hover:border-[var(--stroke-strong)] hover:shadow-[0_18px_32px_rgba(15,42,71,0.12)]",
        isHighlighted && "border-[var(--coral-sunset)] ring-2 ring-[var(--coral-sunset)]",
        isDragging && "rotate-[0.4deg] opacity-70 shadow-[0_22px_40px_rgba(15,42,71,0.18)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
      data-highlighted={isHighlighted ? "true" : "false"}
    >
      <div className="flex items-start justify-between gap-3">
        {isEditing ? (
          <form
            className="w-full space-y-3"
            onPointerDown={(event) => event.stopPropagation()}
            onSubmit={(event) => {
              event.preventDefault();
              const trimmedTitle = title.trim();
              if (!trimmedTitle) {
                setTitleError("Title cannot be empty.");
                return;
              }
              onUpdate(card.id, trimmedTitle, details.trim());
              setTitleError("");
              setIsEditing(false);
            }}
          >
            <input
              value={title}
              onChange={(event) => {
                setTitle(event.target.value);
                if (titleError) {
                  setTitleError("");
                }
              }}
              className={clsx(
                "focus-ring w-full rounded-xl border px-3 py-2 text-sm font-semibold text-[var(--deep-sea)] outline-none",
                titleError ? "border-red-300" : "border-[var(--stroke)]"
              )}
              aria-label={`Edit title for ${card.title}`}
              aria-invalid={titleError ? "true" : "false"}
            />
            {titleError && (
              <p
                role="alert"
                className="text-xs font-semibold text-red-700"
              >
                {titleError}
              </p>
            )}
            <textarea
              value={details}
              onChange={(event) => setDetails(event.target.value)}
              className="focus-ring w-full resize-none rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm leading-6 text-[var(--slate)] outline-none"
              aria-label={`Edit details for ${card.title}`}
              rows={3}
            />
            <div className="flex items-center gap-2">
              <button
                type="submit"
                className="focus-ring rounded-full px-3.5 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-white transition hover:brightness-110"
                style={{
                  background:
                    "linear-gradient(135deg, var(--pacific-blue), var(--aqua-mist))",
                  boxShadow: "0 8px 18px rgba(123, 196, 188, 0.22)",
                }}
              >
                Save
              </button>
              <button
                type="button"
                onClick={exitEdit}
                className="focus-ring rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--slate)] transition hover:border-[var(--stroke-strong)] hover:text-[var(--deep-sea)]"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <>
            <div className="min-w-0">
              <h4 className="break-words font-display text-base font-semibold leading-snug text-[var(--deep-sea)]">
                {card.title}
              </h4>
              <p className="mt-2 break-words text-sm leading-6 text-[var(--slate)]">
                {card.details}
              </p>
            </div>
            <div
              className="flex shrink-0 flex-col items-end gap-1 opacity-70 transition-opacity duration-200 group-hover/card:opacity-100"
              onPointerDown={(event) => event.stopPropagation()}
            >
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="focus-ring rounded-full border border-transparent px-2.5 py-1 text-xs font-semibold text-[var(--slate)] transition hover:border-[var(--stroke)] hover:bg-[var(--surface-muted)] hover:text-[var(--pacific-blue)]"
                aria-label={`Edit ${card.title}`}
              >
                Edit
              </button>
              <button
                type="button"
                onClick={() => onDelete(card.id)}
                className="focus-ring rounded-full border border-transparent px-2.5 py-1 text-xs font-semibold text-[var(--slate)] transition hover:border-red-200 hover:bg-red-50 hover:text-red-600"
                aria-label={`Delete ${card.title}`}
              >
                Remove
              </button>
            </div>
          </>
        )}
      </div>
    </article>
  );
};
