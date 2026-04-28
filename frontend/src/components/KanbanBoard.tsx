"use client";

import { useEffect, useMemo, useState } from "react";
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
import { loadBoard, saveBoard } from "@/lib/boardApi";
import {
  createId,
  createTimestamp,
  moveCard,
  type BoardData,
} from "@/lib/kanban";

const getCardPositions = (board: BoardData) =>
  new Map(
    board.columns.flatMap((column) =>
      column.cardIds.map((cardId, index) => [
        cardId,
        `${column.id}:${index}`,
      ] as const)
    )
  );

const getChangedCardIds = (previous: BoardData, next: BoardData) => {
  const changed = new Set<string>();
  const previousPositions = getCardPositions(previous);
  const nextPositions = getCardPositions(next);

  for (const [cardId, card] of Object.entries(next.cards)) {
    const previousCard = previous.cards[cardId];
    if (!previousCard) {
      changed.add(cardId);
      continue;
    }
    if (
      previousCard.title !== card.title ||
      previousCard.details !== card.details ||
      previousPositions.get(cardId) !== nextPositions.get(cardId)
    ) {
      changed.add(cardId);
    }
  }

  return changed;
};

export const KanbanBoard = () => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "error">("idle");
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isAiSending, setIsAiSending] = useState(false);
  const [aiError, setAiError] = useState("");
  const [highlightedCardIds, setHighlightedCardIds] = useState<Set<string>>(
    new Set()
  );

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  useEffect(() => {
    let isMounted = true;

    loadBoard()
      .then((loadedBoard) => {
        if (isMounted) {
          setBoard(loadedBoard);
          setSaveStatus("idle");
        }
      })
      .catch(() => {
        if (isMounted) {
          setSaveStatus("error");
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (highlightedCardIds.size === 0) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      setHighlightedCardIds(new Set());
    }, 4000);

    return () => window.clearTimeout(timeoutId);
  }, [highlightedCardIds]);

  const updateBoard = (updater: (board: BoardData) => BoardData) => {
    if (!board) {
      return;
    }
    const nextBoard = updater(board);
    setBoard(nextBoard);
    setSaveStatus("saving");
    saveBoard(nextBoard)
      .then((savedBoard) => {
        setBoard(savedBoard);
        setSaveStatus("idle");
      })
      .catch(() => {
        setSaveStatus("error");
      });
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

    updateBoard((prev) => ({
      ...prev,
      columns: moveCard(prev.columns, active.id as string, over.id as string),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    updateBoard((prev) => ({
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    const now = createTimestamp();
    updateBoard((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [id]: {
          id,
          title,
          details: details || "No details yet.",
          createdAt: now,
          updatedAt: now,
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
    updateBoard((prev) => ({
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
    updateBoard((prev) => {
      return {
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
      };
    });
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
      const response = await sendAiMessage(message, chatHistory);
      setChatHistory(response.history);
      if (response.board) {
        setHighlightedCardIds(board ? getChangedCardIds(board, response.board) : new Set());
        setBoard(response.board);
        setSaveStatus("idle");
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

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--surface)] px-6 py-12">
        <p className="text-sm font-semibold text-[var(--gray-text)]">Loading board...</p>
      </main>
    );
  }

  if (!board) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--surface)] px-6 py-12">
        <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
          Unable to load board.
        </p>
      </main>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <main className="relative mx-auto flex min-h-screen max-w-[1700px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                {saveStatus === "saving" ? "Saving changes..." : "Changes saved."}
              </p>
              {saveStatus === "error" && (
                <p className="mt-2 text-sm font-semibold text-red-700">
                  Unable to save board.
                </p>
              )}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="grid gap-6 lg:grid-cols-2 2xl:grid-cols-5">
              {board.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  highlightedCardIds={highlightedCardIds}
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
