"use client";

import { FormEvent, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";

const SESSION_KEY = "pm-mvp-authenticated";
const USERNAME = "user";
const PASSWORD = "password";

export const AppShell = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(
    () =>
      typeof window !== "undefined" &&
      window.localStorage.getItem(SESSION_KEY) === "true"
  );
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

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
        <div className="sticky top-0 z-20 border-b border-[var(--stroke)] bg-white/90 px-6 py-3 backdrop-blur">
          <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4">
            <p className="text-sm font-semibold text-[var(--navy-dark)]">
              Signed in as user
            </p>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
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
    <main className="flex min-h-screen items-center justify-center bg-[var(--surface)] px-6 py-12">
      <section className="w-full max-w-sm rounded-2xl border border-[var(--stroke)] bg-white p-6 shadow-[var(--shadow)]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--gray-text)]">
            Project Management MVP
          </p>
          <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
            Sign in
          </h1>
        </div>

        <form className="mt-8 flex flex-col gap-4" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-2 text-sm font-semibold text-[var(--navy-dark)]">
            Username
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="rounded-xl border border-[var(--stroke)] px-3 py-2 text-base font-normal outline-none transition focus:border-[var(--primary-blue)]"
              autoComplete="username"
            />
          </label>
          <label className="flex flex-col gap-2 text-sm font-semibold text-[var(--navy-dark)]">
            Password
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="rounded-xl border border-[var(--stroke)] px-3 py-2 text-base font-normal outline-none transition focus:border-[var(--primary-blue)]"
              type="password"
              autoComplete="current-password"
            />
          </label>
          {error && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">
              {error}
            </p>
          )}
          <button
            type="submit"
            className="mt-2 rounded-xl bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold text-white transition hover:opacity-90"
          >
            Sign in
          </button>
        </form>
      </section>
    </main>
  );
};
