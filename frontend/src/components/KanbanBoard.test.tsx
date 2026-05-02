import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import type { BoardData } from "@/lib/kanban";
import type { BoardDetail } from "@/lib/boardApi";

const TIMESTAMP = "2026-01-01T00:00:00Z";

const buildBoardData = (): BoardData => ({
  version: 1,
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
    { id: "col-progress", title: "In Progress", cardIds: ["card-3"] },
    { id: "col-done", title: "Done", cardIds: [] },
  ],
  cards: {
    "card-1": {
      id: "card-1",
      title: "Align roadmap themes",
      details: "Draft quarterly themes with impact statements and metrics.",
      createdAt: TIMESTAMP,
      updatedAt: TIMESTAMP,
      priority: null,
      dueDate: null,
      labels: [],
      assignee: null,
    },
    "card-2": {
      id: "card-2",
      title: "Gather customer signals",
      details: "Review support tags, sales notes, and churn feedback.",
      createdAt: TIMESTAMP,
      updatedAt: TIMESTAMP,
      priority: null,
      dueDate: null,
      labels: [],
      assignee: null,
    },
    "card-3": {
      id: "card-3",
      title: "Prototype analytics view",
      details: "Sketch initial dashboard layout and key drill-downs.",
      createdAt: TIMESTAMP,
      updatedAt: TIMESTAMP,
      priority: null,
      dueDate: null,
      labels: [],
      assignee: null,
    },
  },
});

const buildBoardDetail = (data?: BoardData): BoardDetail => ({
  id: 42,
  ownerId: 1,
  title: "Test Board",
  description: "A board for unit tests.",
  position: 0,
  createdAt: TIMESTAMP,
  updatedAt: TIMESTAMP,
  data: data ?? buildBoardData(),
});

const installFetchMock = (
  options: { aiBoard?: BoardData; aiStatus?: number; aiBody?: unknown } = {}
) => {
  const { aiBoard, aiStatus = 200, aiBody } = options;
  let savedDetail = buildBoardDetail();
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = typeof input === "string" ? input : input.toString();

      if (path.includes("/ai/chat")) {
        if (aiStatus !== 200) {
          return Response.json(
            aiBody ?? { detail: "Unable to reach AI assistant." },
            { status: aiStatus }
          );
        }
        const responseBoard = aiBoard
          ? { ...savedDetail, data: aiBoard, updatedAt: new Date().toISOString() }
          : null;
        if (responseBoard) {
          savedDetail = responseBoard;
        }
        return Response.json({
          assistantMessage: aiBoard ? "Created the AI card." : "No board changes.",
          board: responseBoard,
          operationSummary: aiBoard ? "Added a card." : null,
          history: [
            { role: "user", content: "Create a launch notes card" },
            {
              role: "assistant",
              content: aiBoard ? "Created the AI card." : "No board changes.",
            },
          ],
        });
      }

      if (path.match(/\/api\/boards\/\d+\/data$/) && init?.method === "PUT") {
        const body = JSON.parse(init.body as string);
        savedDetail = {
          ...savedDetail,
          data: body.data,
          updatedAt: new Date().toISOString(),
        };
        return Response.json(savedDetail);
      }

      if (path.match(/\/api\/boards\/\d+$/)) {
        return Response.json(savedDetail);
      }

      return Response.json(savedDetail);
    }
  );
  vi.stubGlobal("fetch", fetchMock);
  return { fetchMock };
};

const noop = () => {};

describe("KanbanBoard", () => {
  beforeEach(() => {
    window.localStorage.setItem(
      "pm-session-v1",
      JSON.stringify({
        token: "fake-token",
        expiresAt: new Date(Date.now() + 3600_000).toISOString(),
      })
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  it("renders the board title", () => {
    installFetchMock();
    render(<KanbanBoard board={buildBoardDetail()} onBoardChanged={noop} />);

    expect(screen.getAllByRole("heading", { name: "Test Board" }).length).toBeGreaterThan(
      0
    );
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(3);
  });

  it("renames a column and persists the change", async () => {
    const { fetchMock } = installFetchMock();
    render(<KanbanBoard board={buildBoardDetail()} onBoardChanged={noop} />);

    const column = screen.getByTestId("column-col-backlog");
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");

    expect(input).toHaveValue("New Name");
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringMatching(/\/api\/boards\/42\/data$/),
        expect.objectContaining({ method: "PUT" })
      );
    });
  });

  it("adds and removes a card", async () => {
    installFetchMock();
    render(<KanbanBoard board={buildBoardDetail()} onBoardChanged={noop} />);

    const column = screen.getAllByTestId(/column-/i)[0];
    const addButton = within(column).getByRole("button", { name: /add a card/i });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(
      within(column).getByRole("button", { name: /add card/i })
    );

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("edits a card and saves it", async () => {
    const { fetchMock } = installFetchMock();
    render(<KanbanBoard board={buildBoardDetail()} onBoardChanged={noop} />);

    const column = screen.getByTestId("column-col-backlog");
    await userEvent.click(
      within(column).getByRole("button", { name: /edit align roadmap themes/i })
    );
    const titleInput = within(column).getByLabelText(
      /edit title for align roadmap themes/i
    );
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Updated roadmap themes");
    await userEvent.click(within(column).getByRole("button", { name: "Save" }));

    expect(within(column).getByText("Updated roadmap themes")).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringMatching(/\/api\/boards\/42\/data$/),
        expect.objectContaining({ method: "PUT" })
      );
    });
  });

  it("sends an AI message and applies the board update", async () => {
    const aiBoardData = buildBoardData();
    aiBoardData.cards["card-ai"] = {
      id: "card-ai",
      title: "Launch notes",
      details: "Draft release notes with the AI assistant.",
      createdAt: TIMESTAMP,
      updatedAt: TIMESTAMP,
      priority: null,
      dueDate: null,
      labels: [],
      assignee: null,
    };
    aiBoardData.columns[0].cardIds.push("card-ai");
    const { fetchMock } = installFetchMock({ aiBoard: aiBoardData });

    render(<KanbanBoard board={buildBoardDetail()} onBoardChanged={noop} />);

    await screen.findByRole("heading", { name: "Board Assistant" });
    await userEvent.type(
      screen.getByLabelText("Message"),
      "Create a launch notes card"
    );
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Created the AI card.")).toBeInTheDocument();
    const aiCard = screen.getByTestId("card-card-ai");
    expect(within(aiCard).getByText("Launch notes")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/boards\/42\/ai\/chat$/),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("shows AI errors when the request fails", async () => {
    installFetchMock({ aiStatus: 502, aiBody: "Nope" });
    render(<KanbanBoard board={buildBoardDetail()} onBoardChanged={noop} />);

    await screen.findByRole("heading", { name: "Board Assistant" });
    await userEvent.type(screen.getByLabelText("Message"), "Help");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => {
      expect(screen.getByText("Unable to reach AI assistant.")).toBeInTheDocument();
    });
  });

  it("surfaces backend AI conflict details", async () => {
    installFetchMock({
      aiStatus: 409,
      aiBody: {
        detail:
          "Board changed while the AI was responding. Please retry the request.",
      },
    });
    render(<KanbanBoard board={buildBoardDetail()} onBoardChanged={noop} />);

    await screen.findByRole("heading", { name: "Board Assistant" });
    await userEvent.type(screen.getByLabelText("Message"), "Help");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => {
      expect(
        screen.getByText(
          "Board changed while the AI was responding. Please retry the request."
        )
      ).toBeInTheDocument();
    });
  });
});
