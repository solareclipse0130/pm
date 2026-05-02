"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import type { BoardSummary } from "@/lib/boardApi";

type BoardSwitcherProps = {
  boards: BoardSummary[];
  status: "loading" | "ready" | "error";
  error: string;
  selectedBoardId: number | null;
  busyBoardId: number | null;
  onSelect: (boardId: number) => void;
  onCreate: (title: string) => Promise<void> | void;
  onRename: (boardId: number, title: string) => Promise<void> | void;
  onDelete: (boardId: number) => Promise<void> | void;
};

export const BoardSwitcher = ({
  boards,
  status,
  error,
  selectedBoardId,
  busyBoardId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: BoardSwitcherProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameTitle, setRenameTitle] = useState("");

  const containerRef = useRef<HTMLDivElement | null>(null);
  const renameInputRef = useRef<HTMLInputElement | null>(null);
  const createInputRef = useRef<HTMLInputElement | null>(null);

  const selected = boards.find((board) => board.id === selectedBoardId) ?? null;
  const triggerLabel = selected?.title ?? "Select a board";

  const closePanel = useCallback(() => {
    setIsOpen(false);
    setShowCreate(false);
    setNewTitle("");
    setRenamingId(null);
    setRenameTitle("");
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        closePanel();
      }
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") closePanel();
    };
    window.addEventListener("mousedown", handleClickOutside);
    window.addEventListener("keydown", handleKey);
    return () => {
      window.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("keydown", handleKey);
    };
  }, [isOpen, closePanel]);

  useEffect(() => {
    if (renamingId !== null) {
      renameInputRef.current?.focus();
      renameInputRef.current?.select();
    }
  }, [renamingId]);

  useEffect(() => {
    if (showCreate) {
      createInputRef.current?.focus();
    }
  }, [showCreate]);

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const title = newTitle.trim();
    if (!title) return;
    await onCreate(title);
    setNewTitle("");
    setShowCreate(false);
    setIsOpen(false);
  };

  const handleRenameSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (renamingId === null) return;
    const title = renameTitle.trim();
    if (!title) return;
    await onRename(renamingId, title);
    setRenamingId(null);
    setRenameTitle("");
  };

  const handleStartRename = (board: BoardSummary) => {
    setRenamingId(board.id);
    setRenameTitle(board.title);
  };

  const handleSelect = (boardId: number) => {
    onSelect(boardId);
    closePanel();
  };

  const handleDelete = async (boardId: number) => {
    await onDelete(boardId);
  };

  return (
    <div
      ref={containerRef}
      className="relative inline-flex"
      data-testid="board-switcher"
    >
      <button
        type="button"
        className={`focus-ring inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.32em] transition ${
          isOpen
            ? "border-[var(--pacific-blue)] bg-white text-[var(--pacific-blue)]"
            : "border-[var(--stroke)] bg-white/70 text-[var(--slate)] hover:border-[var(--pacific-blue)] hover:text-[var(--pacific-blue)]"
        }`}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label="Switch board"
        onClick={() => setIsOpen((value) => !value)}
        disabled={status === "loading"}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-[var(--coral-sunset)]" />
        <span className="max-w-[16rem] truncate normal-case tracking-normal text-[var(--deep-sea)]">
          {triggerLabel}
        </span>
        <span aria-hidden className="text-[10px] text-[var(--slate)]">
          {isOpen ? "▴" : "▾"}
        </span>
      </button>

      {isOpen && (
        <div
          role="menu"
          aria-label="Boards"
          className="absolute left-0 top-full z-30 mt-2 w-80 max-w-[90vw] rounded-2xl border border-[var(--stroke)] bg-white/95 p-2 shadow-[var(--shadow-lift)] backdrop-blur"
          data-testid="board-switcher-panel"
        >
          {status === "loading" && (
            <p className="px-3 py-2 text-xs font-semibold text-[var(--slate)]">
              Loading boards...
            </p>
          )}
          {status === "error" && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">
              {error || "Unable to load boards."}
            </p>
          )}
          {status === "ready" && error && (
            <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] font-semibold text-amber-700">
              {error}
            </p>
          )}

          <ul
            className="flex max-h-[60vh] flex-col gap-1 overflow-y-auto py-1"
            data-testid="board-list"
          >
            {boards.map((board) => {
              const isSelected = board.id === selectedBoardId;
              const isRenaming = renamingId === board.id;
              const isBusy = busyBoardId === board.id;

              if (isRenaming) {
                return (
                  <li key={board.id} data-testid={`board-item-${board.id}`}>
                    <form
                      className="flex items-center gap-1 rounded-xl border border-[var(--pacific-blue)] bg-white px-2 py-1"
                      onSubmit={handleRenameSubmit}
                    >
                      <input
                        ref={renameInputRef}
                        aria-label={`Rename ${board.title}`}
                        value={renameTitle}
                        onChange={(event) =>
                          setRenameTitle(event.target.value)
                        }
                        onKeyDown={(event) => {
                          if (event.key === "Escape") {
                            event.preventDefault();
                            event.stopPropagation();
                            setRenamingId(null);
                            setRenameTitle("");
                          }
                        }}
                        className="focus-ring flex-1 rounded-lg bg-transparent px-2 py-1 text-sm font-semibold text-[var(--deep-sea)] outline-none"
                        required
                        maxLength={120}
                      />
                      <button
                        type="submit"
                        disabled={isBusy}
                        className="focus-ring rounded-full bg-[var(--pacific-blue)] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        Save
                      </button>
                      <button
                        type="button"
                        className="focus-ring rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--slate)] hover:text-[var(--deep-sea)]"
                        onClick={() => {
                          setRenamingId(null);
                          setRenameTitle("");
                        }}
                      >
                        Cancel
                      </button>
                    </form>
                  </li>
                );
              }

              return (
                <li
                  key={board.id}
                  data-testid={`board-item-${board.id}`}
                  className={`group flex items-center gap-1 rounded-xl px-2 py-1 transition ${
                    isSelected
                      ? "bg-[var(--foam)]"
                      : "hover:bg-[var(--surface-muted)]"
                  }`}
                >
                  <button
                    type="button"
                    role="menuitemradio"
                    aria-checked={isSelected}
                    aria-current={isSelected ? "true" : undefined}
                    className="focus-ring flex flex-1 items-center gap-2 truncate rounded-lg px-2 py-1 text-left text-sm font-semibold text-[var(--deep-sea)]"
                    onClick={() => handleSelect(board.id)}
                    title={board.title}
                  >
                    <span
                      aria-hidden
                      className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                        isSelected
                          ? "bg-[var(--pacific-blue)]"
                          : "bg-[var(--stroke-strong)]"
                      }`}
                    />
                    <span className="truncate">{board.title}</span>
                  </button>
                  <div
                    className={`flex shrink-0 items-center gap-1 transition ${
                      isSelected
                        ? "opacity-100"
                        : "opacity-0 group-hover:opacity-100"
                    }`}
                  >
                    <button
                      type="button"
                      aria-label={`Rename ${board.title}`}
                      onClick={() => handleStartRename(board)}
                      disabled={isBusy}
                      className="focus-ring rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--slate)] hover:text-[var(--pacific-blue)] disabled:opacity-50"
                    >
                      Rename
                    </button>
                    {boards.length > 1 && (
                      <button
                        type="button"
                        aria-label={`Delete ${board.title}`}
                        onClick={() => handleDelete(board.id)}
                        disabled={isBusy}
                        className="focus-ring rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--slate)] hover:text-[var(--coral-sunset)] disabled:opacity-50"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
            {status === "ready" && boards.length === 0 && (
              <li className="px-3 py-2 text-xs font-semibold text-[var(--slate)]">
                No boards yet.
              </li>
            )}
          </ul>

          <div className="mt-1 border-t border-[var(--stroke)] pt-2">
            {showCreate ? (
              <form
                className="flex items-center gap-1 rounded-xl border border-dashed border-[var(--pacific-blue)] bg-white px-2 py-1"
                onSubmit={handleCreate}
              >
                <input
                  ref={createInputRef}
                  aria-label="Board name"
                  value={newTitle}
                  onChange={(event) => setNewTitle(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Escape") {
                      event.preventDefault();
                      event.stopPropagation();
                      setShowCreate(false);
                      setNewTitle("");
                    }
                  }}
                  placeholder="Board name"
                  className="focus-ring flex-1 rounded-lg bg-transparent px-2 py-1 text-sm font-semibold text-[var(--deep-sea)] outline-none placeholder:text-[var(--slate)]"
                  required
                  maxLength={120}
                />
                <button
                  type="submit"
                  disabled={busyBoardId !== null}
                  className="focus-ring rounded-full bg-[var(--pacific-blue)] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Create
                </button>
                <button
                  type="button"
                  className="focus-ring rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--slate)] hover:text-[var(--deep-sea)]"
                  onClick={() => {
                    setShowCreate(false);
                    setNewTitle("");
                  }}
                >
                  Cancel
                </button>
              </form>
            ) : (
              <button
                type="button"
                className="focus-ring flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.18em] text-[var(--pacific-blue)] transition hover:bg-[var(--surface-muted)]"
                onClick={() => setShowCreate(true)}
              >
                <span aria-hidden className="text-base leading-none">
                  +
                </span>
                New board
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
