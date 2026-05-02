import { apiFetch } from "@/lib/authClient";
import type { BoardDetail } from "@/lib/boardApi";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AiChatResponse = {
  assistantMessage: string;
  board: BoardDetail | null;
  operationSummary: string | null;
  history: ChatMessage[];
};

const readErrorDetail = async (response: Response): Promise<string> => {
  try {
    const body = await response.json();
    return typeof body.detail === "string" ? body.detail : "";
  } catch {
    return "";
  }
};

export const sendAiMessage = async (
  boardId: number,
  message: string,
  history: ChatMessage[]
): Promise<AiChatResponse> => {
  const response = await apiFetch(`/api/boards/${boardId}/ai/chat`, {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail || "Unable to reach AI assistant.");
  }

  return response.json();
};
