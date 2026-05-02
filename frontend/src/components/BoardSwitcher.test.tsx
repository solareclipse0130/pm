import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BoardSwitcher } from "@/components/BoardSwitcher";
import type { BoardSummary } from "@/lib/boardApi";

const sampleBoards: BoardSummary[] = [
  {
    id: 1,
    ownerId: 1,
    title: "Roadmap",
    description: "",
    position: 0,
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
  },
  {
    id: 2,
    ownerId: 1,
    title: "Marketing",
    description: "",
    position: 1,
    createdAt: "2026-01-02T00:00:00Z",
    updatedAt: "2026-01-02T00:00:00Z",
  },
];

const noopAsync = async () => undefined;

const openPanel = async () => {
  await userEvent.click(screen.getByRole("button", { name: /switch board/i }));
};

describe("BoardSwitcher", () => {
  it("shows the selected board in the trigger label", () => {
    render(
      <BoardSwitcher
        boards={sampleBoards}
        status="ready"
        error=""
        selectedBoardId={1}
        busyBoardId={null}
        onSelect={() => {}}
        onCreate={noopAsync}
        onRename={noopAsync}
        onDelete={noopAsync}
      />
    );
    expect(
      screen.getByRole("button", { name: /switch board/i })
    ).toHaveTextContent("Roadmap");
    expect(
      screen.queryByTestId("board-switcher-panel")
    ).not.toBeInTheDocument();
  });

  it("opens the panel and selects another board", async () => {
    const onSelect = vi.fn();
    render(
      <BoardSwitcher
        boards={sampleBoards}
        status="ready"
        error=""
        selectedBoardId={1}
        busyBoardId={null}
        onSelect={onSelect}
        onCreate={noopAsync}
        onRename={noopAsync}
        onDelete={noopAsync}
      />
    );

    await openPanel();
    expect(screen.getByTestId("board-switcher-panel")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Marketing"));
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("disables the trigger while loading", () => {
    render(
      <BoardSwitcher
        boards={[]}
        status="loading"
        error=""
        selectedBoardId={null}
        busyBoardId={null}
        onSelect={() => {}}
        onCreate={noopAsync}
        onRename={noopAsync}
        onDelete={noopAsync}
      />
    );
    expect(screen.getByRole("button", { name: /switch board/i })).toBeDisabled();
  });

  it("creates a new board from the panel footer", async () => {
    const onCreate = vi.fn(async () => undefined);
    render(
      <BoardSwitcher
        boards={sampleBoards}
        status="ready"
        error=""
        selectedBoardId={1}
        busyBoardId={null}
        onSelect={() => {}}
        onCreate={onCreate}
        onRename={noopAsync}
        onDelete={noopAsync}
      />
    );

    await openPanel();
    await userEvent.click(screen.getByRole("button", { name: /new board/i }));
    await userEvent.type(screen.getByLabelText(/board name/i), "Sprint");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));

    expect(onCreate).toHaveBeenCalledWith("Sprint");
  });

  it("renames the selected board", async () => {
    const onRename = vi.fn(async () => undefined);
    render(
      <BoardSwitcher
        boards={sampleBoards}
        status="ready"
        error=""
        selectedBoardId={2}
        busyBoardId={null}
        onSelect={() => {}}
        onCreate={noopAsync}
        onRename={onRename}
        onDelete={noopAsync}
      />
    );

    await openPanel();
    const item = screen.getByTestId("board-item-2");
    await userEvent.click(
      within(item).getByRole("button", { name: /rename marketing/i })
    );
    const renameInput = within(item).getByLabelText(/rename marketing/i);
    await userEvent.clear(renameInput);
    await userEvent.type(renameInput, "Comms");
    await userEvent.click(within(item).getByRole("button", { name: "Save" }));

    expect(onRename).toHaveBeenCalledWith(2, "Comms");
  });

  it("hides the delete button when only one board exists", async () => {
    render(
      <BoardSwitcher
        boards={[sampleBoards[0]]}
        status="ready"
        error=""
        selectedBoardId={1}
        busyBoardId={null}
        onSelect={() => {}}
        onCreate={noopAsync}
        onRename={noopAsync}
        onDelete={noopAsync}
      />
    );
    await openPanel();
    expect(
      screen.queryByRole("button", { name: /delete roadmap/i })
    ).not.toBeInTheDocument();
  });
});
