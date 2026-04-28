import type { BoardData } from "@/lib/kanban";

const AI_CHAT_API_PATH = "/api/ai/chat";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AiChatResponse = {
  assistantMessage: string;
  board: BoardData | null;
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
  message: string,
  history: ChatMessage[]
): Promise<AiChatResponse> => {
  const response = await fetch(AI_CHAT_API_PATH, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail || "Unable to reach AI assistant.");
  }

  return response.json();
};
