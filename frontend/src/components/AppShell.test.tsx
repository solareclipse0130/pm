import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppShell } from "@/components/AppShell";

const buildBoardDetail = () => ({
  id: 1,
  ownerId: 1,
  title: "My Board",
  description: "Default board for getting started.",
  position: 0,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
  data: {
    version: 1,
    columns: [{ id: "col-a", title: "Backlog", cardIds: [] }],
    cards: {},
  },
});

const fakeFutureExpiresAt = () =>
  new Date(Date.now() + 24 * 3600 * 1000).toISOString();

const buildSession = () => ({
  token: "fake-session-token",
  expiresAt: fakeFutureExpiresAt(),
});

const buildAuthResult = (username = "user") => ({
  user: {
    id: 1,
    username,
    displayName: "User",
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
  },
  session: buildSession(),
});

const installAuthFetchMock = ({
  loginStatus = 200,
  signupStatus = 201,
}: { loginStatus?: number; signupStatus?: number } = {}) => {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = typeof input === "string" ? input : input.toString();
      if (path.endsWith("/api/auth/login")) {
        if (loginStatus === 200) {
          return Response.json(buildAuthResult());
        }
        return Response.json(
          { detail: "Invalid username or password." },
          { status: loginStatus }
        );
      }
      if (path.endsWith("/api/auth/signup")) {
        if (signupStatus === 201) {
          return Response.json(buildAuthResult("alice"), { status: 201 });
        }
        return Response.json(
          { detail: "Username is already taken." },
          { status: signupStatus }
        );
      }
      if (path.endsWith("/api/auth/me")) {
        return Response.json({
          id: 1,
          username: "user",
          displayName: "User",
          createdAt: "2026-01-01T00:00:00Z",
          updatedAt: "2026-01-01T00:00:00Z",
        });
      }
      if (path.endsWith("/api/auth/logout")) {
        return Response.json({ loggedOut: true });
      }
      if (path.endsWith("/api/boards") && (!init || init.method === undefined)) {
        return Response.json([
          {
            id: 1,
            ownerId: 1,
            title: "My Board",
            description: "Default board",
            position: 0,
            createdAt: "2026-01-01T00:00:00Z",
            updatedAt: "2026-01-01T00:00:00Z",
          },
        ]);
      }
      if (path.match(/\/api\/boards\/\d+$/)) {
        return Response.json(buildBoardDetail());
      }
      return Response.json({});
    }
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
};

describe("AppShell", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the login screen before authentication", async () => {
    installAuthFetchMock();
    render(<AppShell />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Sign in" })
      ).toBeInTheDocument();
    });
  });

  it("rejects invalid credentials", async () => {
    installAuthFetchMock({ loginStatus: 401 });
    render(<AppShell />);

    await screen.findByRole("heading", { name: "Sign in" });
    await userEvent.type(screen.getByLabelText("Username"), "user");
    await userEvent.type(screen.getByLabelText("Password"), "wrongpass");
    const submitButton = screen
      .getAllByRole("button", { name: "Sign in" })
      .find((node) => node.getAttribute("type") === "submit");
    await userEvent.click(submitButton!);

    expect(
      await screen.findByText("Invalid username or password.")
    ).toBeInTheDocument();
  });

  it("logs in and reaches the workspace", async () => {
    installAuthFetchMock();
    render(<AppShell />);

    await screen.findByRole("heading", { name: "Sign in" });
    await userEvent.type(screen.getByLabelText("Username"), "user");
    await userEvent.type(screen.getByLabelText("Password"), "password");
    const submitButton = screen
      .getAllByRole("button", { name: "Sign in" })
      .find((node) => node.getAttribute("type") === "submit");
    await userEvent.click(submitButton!);

    await waitFor(() => {
      expect(screen.getByText(/signed in as/i)).toBeInTheDocument();
    });
  });

  it("supports switching to the signup tab", async () => {
    installAuthFetchMock();
    render(<AppShell />);

    await screen.findByRole("heading", { name: "Sign in" });
    const signupTab = screen
      .getAllByRole("button", { name: /sign up/i })
      .find((node) => node.tagName === "BUTTON");
    await userEvent.click(signupTab!);

    expect(
      await screen.findByRole("heading", { name: "Create account" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Display name")).toBeInTheDocument();
  });

  it("restores a stored session on load", async () => {
    window.localStorage.setItem(
      "pm-session-v1",
      JSON.stringify(buildSession())
    );
    installAuthFetchMock();
    render(<AppShell />);

    await waitFor(() => {
      expect(screen.getByText(/signed in as/i)).toBeInTheDocument();
    });
  });
});
