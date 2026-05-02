"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Workspace } from "@/components/Workspace";
import {
  AuthUser,
  fetchCurrentUser,
  getStoredSession,
  login,
  logout,
  signup,
} from "@/lib/authClient";

type AuthMode = "login" | "signup";

const BrandMark = ({ size = 36 }: { size?: number }) => (
  <span
    aria-hidden
    className="relative inline-flex shrink-0 items-center justify-center rounded-2xl"
    style={{
      width: size,
      height: size,
      background:
        "linear-gradient(135deg, var(--pacific-blue) 0%, var(--aqua-mist) 70%, var(--deep-sea) 100%)",
      boxShadow: "0 10px 24px rgba(31, 48, 85, 0.22)",
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
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authStatus, setAuthStatus] = useState<"loading" | "ready">("loading");
  const [mode, setMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const session = getStoredSession();
    if (!session) {
      setAuthStatus("ready");
      return;
    }
    fetchCurrentUser()
      .then((current) => {
        if (cancelled) return;
        setUser(current);
        setAuthStatus("ready");
      })
      .catch(() => {
        if (cancelled) return;
        setUser(null);
        setAuthStatus("ready");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSwitchMode = (next: AuthMode) => {
    setMode(next);
    setError("");
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const result =
        mode === "login"
          ? await login(username.trim(), password)
          : await signup(username.trim(), password, displayName.trim() || undefined);
      setUser(result.user);
      setPassword("");
      setDisplayName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to authenticate.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = useCallback(async () => {
    await logout();
    setUser(null);
    setUsername("");
    setPassword("");
    setDisplayName("");
    setError("");
  }, []);

  if (authStatus === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center px-6 py-12">
        <div className="flex items-center gap-3 rounded-full border border-[var(--stroke)] bg-white/80 px-5 py-3 shadow-[var(--shadow-soft)]">
          <span className="pulse-dot h-2 w-2 rounded-full bg-[var(--pacific-blue)]" />
          <p className="text-sm font-semibold text-[var(--deep-sea)]">
            Restoring session...
          </p>
        </div>
      </main>
    );
  }

  if (user) {
    return <Workspace user={user} onLogout={handleLogout} />;
  }

  const isLogin = mode === "login";
  const submitLabel = isLogin ? "Sign in" : "Create account";
  const switchPrompt = isLogin
    ? "New here? Create an account"
    : "Already have an account? Sign in";

  return (
    <main className="relative flex min-h-screen items-center justify-center px-6 py-12">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
      >
        <span
          className="float-slow absolute -left-32 top-12 h-96 w-96 rounded-full opacity-40 blur-3xl"
          style={{ background: "radial-gradient(circle, rgba(72,112,144,0.50), transparent 70%)" }}
        />
        <span
          className="float-slow absolute -right-24 top-1/3 h-[28rem] w-[28rem] rounded-full opacity-40 blur-3xl"
          style={{
            background: "radial-gradient(circle, rgba(132,160,176,0.50), transparent 70%)",
            animationDelay: "1.4s",
          }}
        />
        <span
          className="float-slow absolute bottom-0 left-1/3 h-72 w-72 rounded-full opacity-40 blur-3xl"
          style={{
            background: "radial-gradient(circle, rgba(181,84,74,0.40), transparent 70%)",
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
              "radial-gradient(circle, rgba(72,112,144,0.32), transparent 70%)",
          }}
        />
        <span
          aria-hidden
          className="pointer-events-none absolute -bottom-24 -left-24 h-56 w-56 rounded-full"
          style={{
            background:
              "radial-gradient(circle, rgba(132,160,176,0.28), transparent 70%)",
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

        <div className="relative mt-7 flex gap-2 rounded-full border border-[var(--stroke)] bg-white/70 p-1 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--slate)]">
          <button
            type="button"
            onClick={() => handleSwitchMode("login")}
            className={`flex-1 rounded-full px-3 py-2 transition ${
              isLogin
                ? "bg-[var(--pacific-blue)] text-white shadow-[var(--shadow-soft)]"
                : "text-[var(--slate)] hover:text-[var(--deep-sea)]"
            }`}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => handleSwitchMode("signup")}
            className={`flex-1 rounded-full px-3 py-2 transition ${
              !isLogin
                ? "bg-[var(--pacific-blue)] text-white shadow-[var(--shadow-soft)]"
                : "text-[var(--slate)] hover:text-[var(--deep-sea)]"
            }`}
          >
            Sign up
          </button>
        </div>

        <div className="relative mt-7">
          <h1 className="font-display text-3xl font-semibold leading-tight">
            <span className="shimmer-text">{isLogin ? "Sign in" : "Create account"}</span>
          </h1>
          <p className="mt-2 text-sm leading-6 text-[var(--slate)]">
            {isLogin
              ? "Welcome back. Pick up where you left off and keep your boards moving."
              : "Set up your workspace. Your boards stay private to your account."}
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
              required
              minLength={3}
              maxLength={64}
            />
          </label>
          {!isLogin && (
            <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--slate)]">
              Display name
              <input
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                className="focus-ring rounded-xl border border-[var(--stroke)] bg-white/85 px-4 py-3 text-base font-medium normal-case tracking-normal text-[var(--deep-sea)]"
                autoComplete="name"
                maxLength={120}
              />
            </label>
          )}
          <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--slate)]">
            Password
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="focus-ring rounded-xl border border-[var(--stroke)] bg-white/85 px-4 py-3 text-base font-medium normal-case tracking-normal text-[var(--deep-sea)]"
              type="password"
              autoComplete={isLogin ? "current-password" : "new-password"}
              required
              minLength={8}
              maxLength={256}
            />
          </label>
          {error && (
            <p className="rounded-xl border border-red-200 bg-red-50/90 px-3 py-2 text-sm font-semibold text-red-700">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={isSubmitting}
            className="focus-ring mt-2 rounded-xl px-4 py-3 text-sm font-semibold uppercase tracking-[0.16em] text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            style={{
              background:
                "linear-gradient(135deg, var(--pacific-blue) 0%, var(--aqua-mist) 100%)",
              boxShadow: "0 14px 30px rgba(132, 160, 176, 0.28)",
            }}
          >
            {isSubmitting ? "Working..." : submitLabel}
          </button>
          <button
            type="button"
            className="focus-ring text-center text-xs font-semibold uppercase tracking-[0.18em] text-[var(--slate)] transition hover:text-[var(--pacific-blue)]"
            onClick={() => handleSwitchMode(isLogin ? "signup" : "login")}
          >
            {switchPrompt}
          </button>
        </form>

        <p className="relative mt-6 text-center text-xs text-[var(--slate)]">
          MVP credentials still work:{" "}
          <span className="font-semibold text-[var(--deep-sea)]">user</span> /{" "}
          <span className="font-semibold text-[var(--deep-sea)]">password</span>
        </p>
      </section>
    </main>
  );
};

export { BrandMark };
