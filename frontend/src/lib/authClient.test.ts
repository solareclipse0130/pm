import {
  apiFetch,
  authHeaders,
  clearStoredSession,
  fetchCurrentUser,
  getStoredSession,
  login,
  logout,
  persistSession,
  signup,
} from "@/lib/authClient";

const futureExpiry = () =>
  new Date(Date.now() + 24 * 3600 * 1000).toISOString();

const pastExpiry = () => new Date(Date.now() - 1000).toISOString();

const mockFetchOnce = (response: Response) => {
  vi.stubGlobal("fetch", vi.fn(async () => response));
};

describe("authClient session storage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null when no session is stored", () => {
    expect(getStoredSession()).toBeNull();
    expect(authHeaders()).toEqual({});
  });

  it("persists and reads back a session", () => {
    persistSession({ token: "abc", expiresAt: futureExpiry() });
    expect(getStoredSession()?.token).toBe("abc");
    expect(authHeaders()).toEqual({ Authorization: "Bearer abc" });
  });

  it("treats expired sessions as missing", () => {
    persistSession({ token: "old", expiresAt: pastExpiry() });
    expect(getStoredSession()).toBeNull();
    expect(window.localStorage.getItem("pm-session-v1")).toBeNull();
  });

  it("clears the stored session", () => {
    persistSession({ token: "abc", expiresAt: futureExpiry() });
    clearStoredSession();
    expect(getStoredSession()).toBeNull();
  });
});

describe("authClient login / signup / fetchCurrentUser / logout", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("login persists the returned session", async () => {
    mockFetchOnce(
      Response.json({
        user: {
          id: 1,
          username: "user",
          displayName: "",
          createdAt: "x",
          updatedAt: "x",
        },
        session: { token: "tok", expiresAt: futureExpiry() },
      })
    );
    const result = await login("user", "password");
    expect(result.session.token).toBe("tok");
    expect(getStoredSession()?.token).toBe("tok");
  });

  it("login throws an AuthError on bad credentials", async () => {
    mockFetchOnce(
      Response.json({ detail: "Invalid username or password." }, { status: 401 })
    );
    await expect(login("user", "wrong")).rejects.toThrow(
      "Invalid username or password."
    );
    expect(getStoredSession()).toBeNull();
  });

  it("signup persists the returned session", async () => {
    mockFetchOnce(
      Response.json(
        {
          user: {
            id: 2,
            username: "alice",
            displayName: "Alice",
            createdAt: "x",
            updatedAt: "x",
          },
          session: { token: "newtok", expiresAt: futureExpiry() },
        },
        { status: 201 }
      )
    );
    const result = await signup("alice", "wonderland-9", "Alice");
    expect(result.user.username).toBe("alice");
    expect(getStoredSession()?.token).toBe("newtok");
  });

  it("fetchCurrentUser returns null without a stored session", async () => {
    expect(await fetchCurrentUser()).toBeNull();
  });

  it("fetchCurrentUser clears stored session on 401", async () => {
    persistSession({ token: "tok", expiresAt: futureExpiry() });
    mockFetchOnce(new Response("Unauthorized", { status: 401 }));
    expect(await fetchCurrentUser()).toBeNull();
    expect(getStoredSession()).toBeNull();
  });

  it("logout clears the session even when the request fails", async () => {
    persistSession({ token: "tok", expiresAt: futureExpiry() });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network");
      })
    );
    await expect(logout()).rejects.toThrow();
    expect(getStoredSession()).toBeNull();
  });
});

describe("apiFetch", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("attaches the Authorization header from the stored session", async () => {
    persistSession({ token: "tok", expiresAt: futureExpiry() });
    const fetchMock = vi.fn(async () => Response.json({}));
    vi.stubGlobal("fetch", fetchMock);
    await apiFetch("/api/anywhere");
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer tok");
  });

  it("clears stored session when the response is 401", async () => {
    persistSession({ token: "tok", expiresAt: futureExpiry() });
    const fetchMock = vi.fn(async () =>
      new Response(null, { status: 401 })
    );
    vi.stubGlobal("fetch", fetchMock);
    await apiFetch("/api/anywhere");
    expect(getStoredSession()).toBeNull();
  });
});
