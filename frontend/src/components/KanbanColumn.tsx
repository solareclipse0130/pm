import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

const RENAME_DEBOUNCE_MS = 300;

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  highlightedCardIds?: Set<string>;
  isHighlighted?: boolean;
  accentColor?: string;
  columnIndex?: number;
  onRename: (columnId: string, title: string) => void;
  onAddCard: (columnId: string, title: string, details: string) => void;
  onUpdateCard: (cardId: string, title: string, details: string) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
};

export const KanbanColumn = ({
  column,
  cards,
  highlightedCardIds = new Set(),
  isHighlighted = false,
  accentColor = "var(--pacific-blue)",
  columnIndex = 0,
  onRename,
  onAddCard,
  onUpdateCard,
  onDeleteCard,
}: KanbanColumnProps) => {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });
  const [title, setTitle] = useState(column.title);
  const onRenameRef = useRef(onRename);

  useEffect(() => {
    onRenameRef.current = onRename;
  }, [onRename]);

  useEffect(() => {
    setTitle(column.title);
  }, [column.title]);

  useEffect(() => {
    if (title === column.title) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      onRenameRef.current(column.id, title);
    }, RENAME_DEBOUNCE_MS);
    return () => window.clearTimeout(timeoutId);
  }, [title, column.title, column.id]);

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "group relative flex min-h-[520px] flex-col overflow-hidden rounded-3xl border border-[var(--stroke)] bg-white/85 p-5 shadow-[var(--shadow-soft)] transition-all duration-200",
        "hover:shadow-[var(--shadow)]",
        isOver && "ring-2 ring-offset-2 ring-offset-transparent",
        isHighlighted && "ring-2 ring-[var(--coral-sunset)]"
      )}
      style={
        isOver
          ? ({ ["--tw-ring-color" as string]: accentColor } as React.CSSProperties)
          : undefined
      }
      data-testid={`column-${column.id}`}
      data-column-index={columnIndex}
      data-highlighted={isHighlighted ? "true" : "false"}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-1"
        style={{ background: accentColor }}
      />
      <span
        aria-hidden
        className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full opacity-20 blur-2xl transition-opacity duration-300 group-hover:opacity-30"
        style={{ background: accentColor }}
      />

      <div className="relative flex items-start justify-between gap-3">
        <div className="w-full">
          <div className="flex items-center gap-3">
            <span
              className="inline-flex h-6 items-center gap-1.5 rounded-full px-2.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-white"
              style={{ background: accentColor }}
            >
              <span className="h-1.5 w-1.5 rounded-full bg-white/85" />
              {cards.length} {cards.length === 1 ? "card" : "cards"}
            </span>
          </div>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="focus-ring mt-3 w-full rounded-lg bg-transparent font-display text-lg font-semibold text-[var(--deep-sea)] outline-none"
            aria-label="Column title"
          />
        </div>
      </div>

      <div className="relative mt-4 flex flex-1 flex-col gap-3">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <KanbanCard
              key={card.id}
              card={card}
              isHighlighted={highlightedCardIds.has(card.id)}
              onUpdate={onUpdateCard}
              onDelete={(cardId) => onDeleteCard(column.id, cardId)}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex flex-1 items-center justify-center rounded-2xl border border-dashed border-[var(--stroke)] bg-[var(--surface-muted)]/40 px-3 py-8 text-center text-xs font-semibold uppercase tracking-[0.2em] text-[var(--slate)]">
            Drop a card here
          </div>
        )}
      </div>

      <NewCardForm
        accentColor={accentColor}
        onAdd={(title, details) => onAddCard(column.id, title, details)}
      />
    </section>
  );
};
