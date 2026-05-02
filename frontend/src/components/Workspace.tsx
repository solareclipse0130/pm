"use client";

import { useCallback, useEffect, useState } from "react";
import { BrandMark } from "@/components/AppShell";
import { BoardSwitcher } from "@/components/BoardSwitcher";
import { KanbanBoard } from "@/components/KanbanBoard";
import {
  AuthUser,
} from "@/lib/authClient";
import {
  BoardDetail,
  BoardSummary,
  createBoard,
  deleteBoard,
  getBoard,
  listBoards,
  updateBoardMeta,
} from "@/lib/boardApi";

const SELECTED_BOARD_KEY = "pm-selected-board-id";

const readSelectedBoardId = (): number | null => {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(SELECTED_BOARD_KEY);
  if (!raw) return null;
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) ? parsed : null;
};

const persistSelectedBoardId = (id: number | null) => {
  if (typeof window === "undefined") return;
  if (id === null) {
    window.localStorage.removeItem(SELECTED_BOARD_KEY);
  } else {
    window.localStorage.setItem(SELECTED_BOARD_KEY, String(id));
  }
};

type WorkspaceProps = {
  user: AuthUser;
  onLogout: () => Promise<void> | void;
};

export const Workspace = ({ user, onLogout }: WorkspaceProps) => {
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [boardsStatus, setBoardsStatus] = useState<"loading" | "ready" | "error">(
    "loading"
  );
  const [boardsError, setBoardsError] = useState("");
  const [selectedBoardId, setSelectedBoardId] = useState<number | null>(null);
  const [activeBoard, setActiveBoard] = useState<BoardDetail | null>(null);
  const [activeStatus, setActiveStatus] = useState<"loading" | "ready" | "error">(
    "loading"
  );
  const [activeError, setActiveError] = useState("");
  const [busyBoardId, setBusyBoardId] = useState<number | null>(null);

  const refreshBoards = useCallback(async () => {
    setBoardsStatus("loading");
    setBoardsError("");
    try {
      const result = await listBoards();
      setBoards(result);
      setBoardsStatus("ready");
      const stored = readSelectedBoardId();
      if (stored && result.some((board) => board.id === stored)) {
        setSelectedBoardId(stored);
      } else if (result.length > 0) {
        setSelectedBoardId(result[0].id);
      } else {
        setSelectedBoardId(null);
      }
    } catch (error) {
      setBoardsError(error instanceof Error ? error.message : "Unable to load boards.");
      setBoardsStatus("error");
    }
  }, []);

  useEffect(() => {
    refreshBoards();
  }, [refreshBoards]);

  useEffect(() => {
    persistSelectedBoardId(selectedBoardId);
    if (!selectedBoardId) {
      setActiveBoard(null);
      return;
    }
    let cancelled = false;
    setActiveStatus("loading");
    setActiveError("");
    getBoard(selectedBoardId)
      .then((detail) => {
        if (!cancelled) {
          setActiveBoard(detail);
          setActiveStatus("ready");
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setActiveError(
            error instanceof Error ? error.message : "Unable to load board."
          );
          setActiveStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedBoardId]);

  const handleCreateBoard = async (title: string) => {
    setBusyBoardId(-1);
    try {
      const created = await createBoard(title);
      const summary: BoardSummary = {
        id: created.id,
        ownerId: created.ownerId,
        title: created.title,
        description: created.description,
        position: created.position,
        createdAt: created.createdAt,
        updatedAt: created.updatedAt,
      };
      setBoards((previous) => [...previous, summary]);
      setSelectedBoardId(created.id);
      setActiveBoard(created);
      setActiveStatus("ready");
    } catch (error) {
      setBoardsError(
        error instanceof Error ? error.message : "Unable to create board."
      );
    } finally {
      setBusyBoardId(null);
    }
  };

  const handleRenameBoard = async (boardId: number, title: string) => {
    setBusyBoardId(boardId);
    try {
      const updated = await updateBoardMeta(boardId, { title });
      setBoards((previous) =>
        previous.map((board) =>
          board.id === boardId
            ? { ...board, title: updated.title, updatedAt: updated.updatedAt }
            : board
        )
      );
      if (activeBoard?.id === boardId) {
        setActiveBoard({ ...activeBoard, title: updated.title });
      }
    } catch (error) {
      setBoardsError(
        error instanceof Error ? error.message : "Unable to rename board."
      );
    } finally {
      setBusyBoardId(null);
    }
  };

  const handleDeleteBoard = async (boardId: number) => {
    setBusyBoardId(boardId);
    try {
      await deleteBoard(boardId);
      setBoards((previous) => {
        const next = previous.filter((board) => board.id !== boardId);
        if (selectedBoardId === boardId) {
          setSelectedBoardId(next.length > 0 ? next[0].id : null);
        }
        return next;
      });
    } catch (error) {
      setBoardsError(
        error instanceof Error ? error.message : "Unable to delete board."
      );
    } finally {
      setBusyBoardId(null);
    }
  };

  const handleBoardUpdated = useCallback((next: BoardDetail) => {
    setActiveBoard(next);
    setBoards((previous) =>
      previous.map((board) =>
        board.id === next.id
          ? {
              ...board,
              title: next.title,
              description: next.description,
              updatedAt: next.updatedAt,
            }
          : board
      )
    );
  }, []);

  const greetingName = user.displayName || user.username;

  const boardSwitcher = (
    <BoardSwitcher
      boards={boards}
      status={boardsStatus}
      error={boardsError}
      selectedBoardId={selectedBoardId}
      busyBoardId={busyBoardId}
      onSelect={setSelectedBoardId}
      onCreate={handleCreateBoard}
      onRename={handleRenameBoard}
      onDelete={handleDeleteBoard}
    />
  );

  return (
    <div>
      <div className="sticky top-0 z-20 border-b border-[var(--stroke)] surface-glass px-6 py-3">
        <div className="mx-auto flex max-w-[1700px] items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <BrandMark size={32} />
            <div className="leading-tight">
              <p className="text-[10px] font-semibold uppercase tracking-[0.32em] text-[var(--slate)]">
                Kanban Studio
              </p>
              <p className="text-sm font-semibold text-[var(--deep-sea)]">
                Signed in as {greetingName}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => onLogout()}
            className="focus-ring rounded-full border border-[var(--stroke)] bg-white/70 px-4 py-2 text-sm font-semibold text-[var(--deep-sea)] transition hover:border-[var(--aqua-mist)] hover:text-[var(--aqua-mist)]"
          >
            Logout
          </button>
        </div>
      </div>

      <section className="mx-auto w-full max-w-[1700px] px-4 pt-4">
        {activeStatus === "loading" && (
          <div className="flex min-h-[40vh] items-center justify-center">
            <div className="flex items-center gap-3 rounded-full border border-[var(--stroke)] bg-white/80 px-5 py-3 shadow-[var(--shadow-soft)]">
              <span className="pulse-dot h-2 w-2 rounded-full bg-[var(--pacific-blue)]" />
              <p className="text-sm font-semibold text-[var(--deep-sea)]">
                Loading board...
              </p>
            </div>
          </div>
        )}
        {activeStatus === "error" && (
          <p className="m-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
            {activeError || "Unable to load board."}
          </p>
        )}
        {activeStatus === "ready" && activeBoard && (
          <KanbanBoard
            board={activeBoard}
            onBoardChanged={handleBoardUpdated}
            boardSwitcher={boardSwitcher}
          />
        )}
        {activeStatus === "ready" && !activeBoard && (
          <div className="m-6 flex flex-col gap-4 rounded-2xl border border-[var(--stroke)] bg-white/80 p-6 text-sm font-semibold text-[var(--deep-sea)]">
            <p>Create your first board to get started.</p>
            <div>{boardSwitcher}</div>
          </div>
        )}
      </section>
    </div>
  );
};
