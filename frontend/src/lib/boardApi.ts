import type { BoardData } from "@/lib/kanban";

const BOARD_API_PATH = "/api/board";

export const loadBoard = async (): Promise<BoardData> => {
  const response = await fetch(BOARD_API_PATH);
  if (!response.ok) {
    throw new Error("Unable to load board.");
  }
  return response.json();
};

export const saveBoard = async (board: BoardData): Promise<BoardData> => {
  const response = await fetch(BOARD_API_PATH, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(board),
  });

  if (!response.ok) {
    throw new Error("Unable to save board.");
  }

  return response.json();
};
