"use client";

import { ReactNode, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { AiChatSidebar } from "@/components/AiChatSidebar";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { sendAiMessage, type ChatMessage } from "@/lib/aiApi";
import { updateBoardData, type BoardDetail } from "@/lib/boardApi";
import {
  createId,
  createTimestamp,
  moveCard,
  type BoardData,
} from "@/lib/kanban";

type SaveStatus = "idle" | "saving" | "error";

type BoardChanges = {
  changedCardIds: Set<string>;
  changedColumnIds: Set<string>;
};

type KanbanBoardProps = {
  board: BoardDetail;
  onBoardChanged: (board: BoardDetail) => void;
  boardSwitcher?: ReactNode;
};

const COLUMN_ACCENTS = [
  "var(--pacific-blue)",
  "var(--aqua-mist)",
  "var(--coral-sunset)",
  "var(--deep-sea)",
  "var(--pacific-blue)",
] as const;

const getAccent = (index: number) =>
  COLUMN_ACCENTS[index % COLUMN_ACCENTS.length];

const getCardPositions = (data: BoardData) =>
  new Map(
    data.columns.flatMap((column) =>
      column.cardIds.map((cardId, index) => [
        cardId,
        `${column.id}:${index}`,
      ] as const)
    )
  );

const getBoardChanges = (previous: BoardData, next: BoardData): BoardChanges => {
  const changedCardIds = new Set<string>();
  const changedColumnIds = new Set<string>();
  const previousPositions = getCardPositions(previous);
  const nextPositions = getCardPositions(next);

  for (const [cardId, card] of Object.entries(next.cards)) {
    const previousCard = previous.cards[cardId];
    if (!previousCard) {
      changedCardIds.add(cardId);
      continue;
    }
    if (
      previousCard.title !== card.title ||
      previousCard.details !== card.details ||
      previousCard.priority !== card.priority ||
      previousCard.dueDate !== card.dueDate ||
      previousCard.assignee !== card.assignee ||
      JSON.stringify(previousCard.labels ?? []) !==
        JSON.stringify(card.labels ?? []) ||
      previousPositions.get(cardId) !== nextPositions.get(cardId)
    ) {
      changedCardIds.add(cardId);
    }
  }

  const previousColumnsById = new Map(
    previous.columns.map((column) => [column.id, column])
  );
  for (const column of next.columns) {
    const previousColumn = previousColumnsById.get(column.id);
    if (!previousColumn || previousColumn.title !== column.title) {
      changedColumnIds.add(column.id);
    }
  }

  return { changedCardIds, changedColumnIds };
};

export const KanbanBoard = ({
  board: detail,
  onBoardChanged,
  boardSwitcher,
}: KanbanBoardProps) => {
  const [data, setData] = useState<BoardData>(detail.data);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isAiSending, setIsAiSending] = useState(false);
  const [aiError, setAiError] = useState("");
  const [highlightedCardIds, setHighlightedCardIds] = useState<Set<string>>(
    new Set()
  );
  const [highlightedColumnIds, setHighlightedColumnIds] = useState<Set<string>>(
    new Set()
  );

  const saveQueueRef = useRef<Promise<unknown>>(Promise.resolve());
  const pendingSavesRef = useRef(0);
  const onBoardChangedRef = useRef(onBoardChanged);
  onBoardChangedRef.current = onBoardChanged;
  const detailRef = useRef(detail);
  detailRef.current = detail;

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  // Reset chat + highlight when switching boards. We intentionally key on
  // `detail.id` rather than `detail.data` so transient saves don't blow away
  // the chat panel; the next effect keeps `data` itself in sync.
  useEffect(() => {
    setChatHistory([]);
    setAiError("");
    setHighlightedCardIds(new Set());
    setHighlightedColumnIds(new Set());
  }, [detail.id]);

  // Keep local data in sync with parent when the parent reports a change
  // sourced elsewhere (AI reply, board switch, ...).
  useEffect(() => {
    setData(detail.data);
  }, [detail]);

  useEffect(() => {
    if (highlightedCardIds.size === 0 && highlightedColumnIds.size === 0) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      setHighlightedCardIds(new Set());
      setHighlightedColumnIds(new Set());
    }, 4000);
    return () => window.clearTimeout(timeoutId);
  }, [highlightedCardIds, highlightedColumnIds]);

  const cardsById = useMemo(() => data.cards, [data.cards]);

  const persistData = (next: BoardData) => {
    pendingSavesRef.current += 1;
    setSaveStatus("saving");
    saveQueueRef.current = saveQueueRef.current
      .then(() => updateBoardData(detailRef.current.id, next))
      .then(
        (saved) => {
          pendingSavesRef.current -= 1;
          if (pendingSavesRef.current === 0) {
            setSaveStatus("idle");
          }
          onBoardChangedRef.current(saved);
        },
        () => {
          pendingSavesRef.current -= 1;
          setSaveStatus("error");
        }
      );
  };

  const updateData = (updater: (current: BoardData) => BoardData) => {
    const next = updater(data);
    setData(next);
    persistData(next);
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);
    if (!over || active.id === over.id) {
      return;
    }
    updateData((prev) => ({
      ...prev,
      columns: moveCard(prev.columns, active.id as string, over.id as string),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    updateData((prev) => ({
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    const now = createTimestamp();
    updateData((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [id]: {
          id,
          title,
          details: details || "No details yet.",
          createdAt: now,
          updatedAt: now,
          priority: null,
          dueDate: null,
          labels: [],
          assignee: null,
        },
      },
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    }));
  };

  const handleUpdateCard = (cardId: string, title: string, details: string) => {
    updateData((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [cardId]: {
          ...prev.cards[cardId],
          title,
          details: details || "No details yet.",
          updatedAt: createTimestamp(),
        },
      },
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    updateData((prev) => ({
      ...prev,
      cards: Object.fromEntries(
        Object.entries(prev.cards).filter(([id]) => id !== cardId)
      ),
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? {
              ...column,
              cardIds: column.cardIds.filter((id) => id !== cardId),
            }
          : column
      ),
    }));
  };

  const handleAiMessage = async (message: string) => {
    const optimisticHistory: ChatMessage[] = [
      ...chatHistory,
      { role: "user", content: message },
    ];
    setChatHistory(optimisticHistory);
    setIsAiSending(true);
    setAiError("");

    try {
      const response = await sendAiMessage(detailRef.current.id, message, chatHistory);
      setChatHistory(response.history);
      if (response.board) {
        const previous = data;
        const nextData = response.board.data;
        const changes = getBoardChanges(previous, nextData);
        setHighlightedCardIds(changes.changedCardIds);
        setHighlightedColumnIds(changes.changedColumnIds);
        setData(nextData);
        onBoardChangedRef.current(response.board);
      }
    } catch (error) {
      setChatHistory(chatHistory);
      setAiError(
        error instanceof Error ? error.message : "Unable to reach AI assistant."
      );
    } finally {
      setIsAiSending(false);
    }
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;
  const totalCards = Object.keys(data.cards).length;
  const doneCardIds = new Set(data.columns[data.columns.length - 1]?.cardIds ?? []);
  const completionRatio = totalCards === 0 ? 0 : doneCardIds.size / totalCards;
  const completionPct = Math.round(completionRatio * 100);

  let saveLabel = "All changes saved";
  let saveDotClass = "bg-emerald-500";
  let saveDescription = "Changes saved.";
  if (saveStatus === "saving") {
    saveLabel = "Saving changes";
    saveDotClass = "bg-[var(--pacific-blue)] pulse-dot";
    saveDescription = "Saving changes...";
  } else if (saveStatus === "error") {
    saveLabel = "Save failed";
    saveDotClass = "bg-red-500";
    saveDescription = "Unable to save board.";
  }

  return (
    <div className="relative">
      <main className="relative flex w-full flex-col gap-6 pb-16">
        <header className="relative overflow-hidden rounded-[32px] border border-[var(--stroke)] surface-glass p-8 shadow-[var(--shadow)]">
          <span
            aria-hidden
            className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full opacity-60 blur-3xl"
            style={{
              background: "radial-gradient(circle, rgba(72,112,144,0.32), transparent 70%)",
            }}
          />
          <span
            aria-hidden
            className="pointer-events-none absolute -bottom-32 -left-16 h-72 w-72 rounded-full opacity-50 blur-3xl"
            style={{
              background: "radial-gradient(circle, rgba(132,160,176,0.26), transparent 70%)",
            }}
          />

          <div className="relative flex flex-wrap items-start justify-between gap-6">
            <div className="max-w-2xl">
              {boardSwitcher ?? (
                <div className="inline-flex items-center gap-2 rounded-full border border-[var(--stroke)] bg-white/70 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.32em] text-[var(--slate)]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[var(--coral-sunset)]" />
                  {detail.title}
                </div>
              )}
              <h1 className="mt-4 font-display text-4xl font-semibold leading-tight text-[var(--deep-sea)] md:text-5xl">
                <span className="shimmer-text">{detail.title}</span>
              </h1>
              {detail.description && (
                <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--slate)]">
                  {detail.description}
                </p>
              )}
            </div>

            <div className="flex flex-col items-end gap-3">
              <div
                className="inline-flex items-center gap-2 rounded-full border border-[var(--stroke)] bg-white/80 px-4 py-2 text-xs font-semibold text-[var(--deep-sea)] shadow-[var(--shadow-soft)]"
                aria-live="polite"
                aria-label={saveLabel}
              >
                <span className={`h-2 w-2 rounded-full ${saveDotClass}`} />
                <span className="uppercase tracking-[0.18em]">{saveLabel}</span>
              </div>
              <div className="rounded-2xl border border-[var(--stroke)] bg-white/85 px-5 py-4 shadow-[var(--shadow-soft)]">
                <p className="text-[10px] font-semibold uppercase tracking-[0.32em] text-[var(--slate)]">
                  Focus
                </p>
                <p className="mt-1 text-lg font-semibold text-[var(--pacific-blue)]">
                  {saveDescription}
                </p>
                <div className="mt-3 flex items-center gap-3">
                  <div className="h-1.5 w-32 overflow-hidden rounded-full bg-[var(--surface-muted)]">
                    <div
                      className="h-full rounded-full transition-[width] duration-500"
                      style={{
                        width: `${completionPct}%`,
                        background:
                          "linear-gradient(90deg, var(--pacific-blue), var(--aqua-mist))",
                      }}
                    />
                  </div>
                  <span className="text-xs font-semibold tabular-nums text-[var(--deep-sea)]">
                    {doneCardIds.size}/{totalCards} done
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="relative mt-6 flex flex-wrap items-center gap-3">
            {data.columns.map((column, index) => {
              const accent = getAccent(index);
              return (
                <div
                  key={column.id}
                  className="flex items-center gap-2 rounded-full border border-[var(--stroke)] bg-white/70 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--deep-sea)] transition hover:border-[var(--stroke-strong)] hover:bg-white"
                >
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: accent }}
                  />
                  {column.title}
                  <span className="ml-1 rounded-full bg-[var(--surface-muted)] px-2 py-0.5 text-[10px] font-semibold tabular-nums text-[var(--slate)]">
                    {column.cardIds.length}
                  </span>
                </div>
              );
            })}
          </div>
        </header>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              {data.columns.map((column, index) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => data.cards[cardId])}
                  highlightedCardIds={highlightedCardIds}
                  isHighlighted={highlightedColumnIds.has(column.id)}
                  accentColor={getAccent(index)}
                  columnIndex={index}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onUpdateCard={handleUpdateCard}
                  onDeleteCard={handleDeleteCard}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>

          <AiChatSidebar
            messages={chatHistory}
            isSending={isAiSending}
            error={aiError}
            onSend={handleAiMessage}
          />
        </div>
      </main>
    </div>
  );
};
