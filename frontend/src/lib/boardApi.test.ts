import {
  createBoard,
  deleteBoard,
  getBoard,
  listBoards,
  reorderBoards,
  updateBoardData,
  updateBoardMeta,
} from "@/lib/boardApi";
import { persistSession } from "@/lib/authClient";

const futureExpiry = () =>
  new Date(Date.now() + 24 * 3600 * 1000).toISOString();

const sampleBoardData = () => ({
  version: 1 as const,
  columns: [{ id: "col-a", title: "A", cardIds: [] }],
  cards: {},
});

const sampleBoardDetail = () => ({
  id: 7,
  ownerId: 1,
  title: "Test",
  description: "",
  position: 0,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
  data: sampleBoardData(),
});

describe("boardApi", () => {
  beforeEach(() => {
    window.localStorage.clear();
    persistSession({ token: "tok", expiresAt: futureExpiry() });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  it("listBoards GETs /api/boards with auth", async () => {
    const fetchMock = vi.fn(async () => Response.json([]));
    vi.stubGlobal("fetch", fetchMock);
    await listBoards();
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer tok");
  });

  it("getBoard targets the right URL", async () => {
    const fetchMock = vi.fn(async () => Response.json(sampleBoardDetail()));
    vi.stubGlobal("fetch", fetchMock);
    const detail = await getBoard(7);
    expect(detail.id).toBe(7);
    expect(String(fetchMock.mock.calls[0][0])).toBe("/api/boards/7");
  });

  it("createBoard POSTs the title", async () => {
    const fetchMock = vi.fn(async (_url, init) => {
      const body = JSON.parse(init.body);
      return Response.json({ ...sampleBoardDetail(), title: body.title });
    });
    vi.stubGlobal("fetch", fetchMock);
    const created = await createBoard("Marketing", "Q3");
    expect(created.title).toBe("Marketing");
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body).toEqual({ title: "Marketing", description: "Q3" });
  });

  it("updateBoardMeta PATCHes /api/boards/:id", async () => {
    const fetchMock = vi.fn(async () =>
      Response.json({ ...sampleBoardDetail(), title: "Renamed" })
    );
    vi.stubGlobal("fetch", fetchMock);
    const updated = await updateBoardMeta(7, { title: "Renamed" });
    expect(updated.title).toBe("Renamed");
    expect(fetchMock.mock.calls[0][1].method).toBe("PATCH");
  });

  it("updateBoardData PUTs /api/boards/:id/data", async () => {
    const fetchMock = vi.fn(async () => Response.json(sampleBoardDetail()));
    vi.stubGlobal("fetch", fetchMock);
    await updateBoardData(7, sampleBoardData(), "2026-01-01T00:00:00Z");
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.expectedUpdatedAt).toBe("2026-01-01T00:00:00Z");
    expect(String(fetchMock.mock.calls[0][0])).toBe("/api/boards/7/data");
    expect(fetchMock.mock.calls[0][1].method).toBe("PUT");
  });

  it("deleteBoard issues DELETE", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    await deleteBoard(7);
    expect(fetchMock.mock.calls[0][1].method).toBe("DELETE");
  });

  it("reorderBoards PUTs the new order", async () => {
    const fetchMock = vi.fn(async () => Response.json([]));
    vi.stubGlobal("fetch", fetchMock);
    await reorderBoards([3, 2, 1]);
    expect(String(fetchMock.mock.calls[0][0])).toBe("/api/boards/order");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      boardIds: [3, 2, 1],
    });
  });

  it("surfaces backend detail strings as errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({ detail: "Board changed since you last loaded it." }, {
          status: 409,
        })
      )
    );
    await expect(updateBoardData(7, sampleBoardData())).rejects.toThrow(
      "Board changed since you last loaded it."
    );
  });
});
