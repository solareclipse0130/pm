import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppShell } from "@/components/AppShell";

describe("AppShell", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("shows the login screen before authentication", () => {
    render(<AppShell />);

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Kanban Studio" })).not.toBeInTheDocument();
  });

  it("rejects invalid credentials", async () => {
    render(<AppShell />);

    await userEvent.type(screen.getByLabelText("Username"), "user");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByText("Invalid username or password.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Kanban Studio" })).not.toBeInTheDocument();
  });

  it("accepts the MVP credentials", async () => {
    render(<AppShell />);

    await userEvent.type(screen.getByLabelText("Username"), "user");
    await userEvent.type(screen.getByLabelText("Password"), "password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByRole("heading", { name: "Kanban Studio" })).toBeInTheDocument();
    expect(window.localStorage.getItem("pm-mvp-authenticated")).toBe("true");
  });

  it("restores and clears the local session", async () => {
    window.localStorage.setItem("pm-mvp-authenticated", "true");
    render(<AppShell />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Kanban Studio" })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: "Logout" }));

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(window.localStorage.getItem("pm-mvp-authenticated")).toBeNull();
  });
});
