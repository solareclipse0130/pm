import type { BoardData } from "@/lib/kanban";
import { apiFetch } from "@/lib/authClient";

const BOARDS_PATH = "/api/boards";

export type BoardSummary = {
  id: number;
  ownerId: number;
  title: string;
  description: string;
  position: number;
  createdAt: string;
  updatedAt: string;
};

export type BoardDetail = BoardSummary & {
  data: BoardData;
};

const readErrorDetail = async (response: Response): Promise<string> => {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // ignore
  }
  return response.statusText || `Request failed with status ${response.status}.`;
};

const failOn = async (response: Response, fallback: string): Promise<never> => {
  const detail = await readErrorDetail(response);
  throw new Error(detail || fallback);
};

export const listBoards = async (): Promise<BoardSummary[]> => {
  const response = await apiFetch(BOARDS_PATH);
  if (!response.ok) await failOn(response, "Unable to load boards.");
  return response.json();
};

export const getBoard = async (boardId: number): Promise<BoardDetail> => {
  const response = await apiFetch(`${BOARDS_PATH}/${boardId}`);
  if (!response.ok) await failOn(response, "Unable to load board.");
  return response.json();
};

export const createBoard = async (
  title: string,
  description?: string
): Promise<BoardDetail> => {
  const response = await apiFetch(BOARDS_PATH, {
    method: "POST",
    body: JSON.stringify({ title, description }),
  });
  if (!response.ok) await failOn(response, "Unable to create board.");
  return response.json();
};

export const updateBoardMeta = async (
  boardId: number,
  patch: { title?: string; description?: string }
): Promise<BoardDetail> => {
  const response = await apiFetch(`${BOARDS_PATH}/${boardId}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
  if (!response.ok) await failOn(response, "Unable to update board.");
  return response.json();
};

export const updateBoardData = async (
  boardId: number,
  data: BoardData,
  expectedUpdatedAt?: string
): Promise<BoardDetail> => {
  const body: Record<string, unknown> = { data };
  if (expectedUpdatedAt) body.expectedUpdatedAt = expectedUpdatedAt;
  const response = await apiFetch(`${BOARDS_PATH}/${boardId}/data`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!response.ok) await failOn(response, "Unable to save board.");
  return response.json();
};

export const deleteBoard = async (boardId: number): Promise<void> => {
  const response = await apiFetch(`${BOARDS_PATH}/${boardId}`, {
    method: "DELETE",
  });
  if (!response.ok && response.status !== 204) {
    await failOn(response, "Unable to delete board.");
  }
};

export const reorderBoards = async (
  boardIds: number[]
): Promise<BoardSummary[]> => {
  const response = await apiFetch(`${BOARDS_PATH}/order`, {
    method: "PUT",
    body: JSON.stringify({ boardIds }),
  });
  if (!response.ok) await failOn(response, "Unable to reorder boards.");
  return response.json();
};
