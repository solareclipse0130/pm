"use client";

import { FormEvent, useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";

const SESSION_KEY = "pm-mvp-authenticated";
const USERNAME = "user";
const PASSWORD = "password";

const BrandMark = ({ size = 36 }: { size?: number }) => (
  <span
    aria-hidden
    className="relative inline-flex shrink-0 items-center justify-center rounded-2xl"
    style={{
      width: size,
      height: size,
      background:
        "linear-gradient(135deg, var(--pacific-blue) 0%, var(--aqua-mist) 70%, var(--deep-sea) 100%)",
      boxShadow: "0 10px 24px rgba(15, 42, 71, 0.22)",
    }}
  >
    <span
      className="absolute rounded-md bg-white/95"
      style={{ width: size * 0.18, height: size * 0.42, left: size * 0.26, top: size * 0.22 }}
    />
    <span
      className="absolute rounded-md"
      style={{
        width: size * 0.18,
        height: size * 0.28,
        left: size * 0.5,
        top: size * 0.36,
        background: "var(--coral-sunset)",
      }}
    />
  </span>
);

export const AppShell = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (window.localStorage.getItem(SESSION_KEY) === "true") {
      // Restoring persisted session must run after mount to avoid SSR/CSR
      // hydration mismatch on the static export.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIsAuthenticated(true);
    }
  }, []);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (username === USERNAME && password === PASSWORD) {
      window.localStorage.setItem(SESSION_KEY, "true");
      setIsAuthenticated(true);
      setError("");
      setPassword("");
      return;
    }

    window.localStorage.removeItem(SESSION_KEY);
    setIsAuthenticated(false);
    setError("Invalid username or password.");
  };

  const handleLogout = () => {
    window.localStorage.removeItem(SESSION_KEY);
    setIsAuthenticated(false);
    setUsername("");
    setPassword("");
    setError("");
  };

  if (isAuthenticated) {
    return (
      <div>
        <div className="sticky top-0 z-20 border-b border-[var(--stroke)] surface-glass px-6 py-3">
          <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <BrandMark size={32} />
              <div className="leading-tight">
                <p className="text-[10px] font-semibold uppercase tracking-[0.32em] text-[var(--slate)]">
                  Kanban Studio
                </p>
                <p className="text-sm font-semibold text-[var(--deep-sea)]">
                  Signed in as user
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="focus-ring rounded-full border border-[var(--stroke)] bg-white/70 px-4 py-2 text-sm font-semibold text-[var(--deep-sea)] transition hover:border-[var(--aqua-mist)] hover:text-[var(--aqua-mist)]"
            >
              Logout
            </button>
          </div>
        </div>
        <KanbanBoard />
      </div>
    );
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center px-6 py-12">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
      >
        <span
          className="float-slow absolute -left-32 top-12 h-96 w-96 rounded-full opacity-40 blur-3xl"
          style={{ background: "radial-gradient(circle, rgba(0,133,161,0.55), transparent 70%)" }}
        />
        <span
          className="float-slow absolute -right-24 top-1/3 h-[28rem] w-[28rem] rounded-full opacity-40 blur-3xl"
          style={{
            background: "radial-gradient(circle, rgba(123,196,188,0.55), transparent 70%)",
            animationDelay: "1.4s",
          }}
        />
        <span
          className="float-slow absolute bottom-0 left-1/3 h-72 w-72 rounded-full opacity-40 blur-3xl"
          style={{
            background: "radial-gradient(circle, rgba(242,113,94,0.45), transparent 70%)",
            animationDelay: "2.8s",
          }}
        />
      </div>

      <section className="relative w-full max-w-md overflow-hidden rounded-[28px] border border-[var(--stroke)] surface-glass p-8 shadow-[var(--shadow-lift)]">
        <span
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 h-56 w-56 rounded-full"
          style={{
            background:
              "radial-gradient(circle, rgba(0,133,161,0.35), transparent 70%)",
          }}
        />
        <span
          aria-hidden
          className="pointer-events-none absolute -bottom-24 -left-24 h-56 w-56 rounded-full"
          style={{
            background:
              "radial-gradient(circle, rgba(123,196,188,0.30), transparent 70%)",
          }}
        />

        <div className="relative flex items-center gap-3">
          <BrandMark size={42} />
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-[var(--slate)]">
              Project Management
            </p>
            <p className="font-display text-lg font-semibold text-[var(--deep-sea)]">
              Kanban Studio
            </p>
          </div>
        </div>

        <div className="relative mt-7">
          <h1 className="font-display text-3xl font-semibold leading-tight">
            <span className="shimmer-text">Sign in</span>
          </h1>
          <p className="mt-2 text-sm leading-6 text-[var(--slate)]">
            Welcome back. Pick up where you left off and keep the board moving.
          </p>
        </div>

        <form className="relative mt-7 flex flex-col gap-4" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--slate)]">
            Username
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="focus-ring rounded-xl border border-[var(--stroke)] bg-white/85 px-4 py-3 text-base font-medium normal-case tracking-normal text-[var(--deep-sea)]"
              autoComplete="username"
            />
          </label>
          <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--slate)]">
            Password
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="focus-ring rounded-xl border border-[var(--stroke)] bg-white/85 px-4 py-3 text-base font-medium normal-case tracking-normal text-[var(--deep-sea)]"
              type="password"
              autoComplete="current-password"
            />
          </label>
          {error && (
            <p className="rounded-xl border border-red-200 bg-red-50/90 px-3 py-2 text-sm font-semibold text-red-700">
              {error}
            </p>
          )}
          <button
            type="submit"
            className="focus-ring mt-2 rounded-xl px-4 py-3 text-sm font-semibold uppercase tracking-[0.16em] text-white transition hover:brightness-110"
            style={{
              background:
                "linear-gradient(135deg, var(--pacific-blue) 0%, var(--aqua-mist) 100%)",
              boxShadow: "0 14px 30px rgba(123, 196, 188, 0.28)",
            }}
          >
            Sign in
          </button>
        </form>

        <p className="relative mt-6 text-center text-xs text-[var(--slate)]">
          MVP credentials: <span className="font-semibold text-[var(--deep-sea)]">user</span> / <span className="font-semibold text-[var(--deep-sea)]">password</span>
        </p>
      </section>
    </main>
  );
};
