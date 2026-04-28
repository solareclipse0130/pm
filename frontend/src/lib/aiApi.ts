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
    throw new Error("Unable to reach AI assistant.");
  }

  return response.json();
};
