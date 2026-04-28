import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData, type BoardData } from "@/lib/kanban";

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];
const cloneBoard = (): BoardData => structuredClone(initialData);

const mockBoardApi = (board = cloneBoard()) => {
  let savedBoard = board;
  const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "PUT") {
      savedBoard = JSON.parse(init.body as string);
      return Response.json(savedBoard);
    }
    return Response.json(savedBoard);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
};

describe("KanbanBoard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders five columns from the backend", async () => {
    mockBoardApi();
    render(<KanbanBoard />);

    expect(await screen.findByRole("heading", { name: "Kanban Studio" })).toBeInTheDocument();
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    const fetchMock = mockBoardApi();
    render(<KanbanBoard />);
    const column = await screen.findByTestId("column-col-backlog");
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");

    expect(input).toHaveValue("New Name");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/board",
      expect.objectContaining({ method: "PUT" })
    );
  });

  it("adds and removes a card", async () => {
    mockBoardApi();
    render(<KanbanBoard />);
    await screen.findByRole("heading", { name: "Kanban Studio" });
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("edits a card and saves it", async () => {
    const fetchMock = mockBoardApi();
    render(<KanbanBoard />);
    const column = await screen.findByTestId("column-col-backlog");

    await userEvent.click(within(column).getByRole("button", {
      name: /edit align roadmap themes/i,
    }));
    const titleInput = within(column).getByLabelText(
      /edit title for align roadmap themes/i
    );
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Updated roadmap themes");
    await userEvent.click(within(column).getByRole("button", { name: "Save" }));

    expect(within(column).getByText("Updated roadmap themes")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/board",
      expect.objectContaining({ method: "PUT" })
    );
  });
});
