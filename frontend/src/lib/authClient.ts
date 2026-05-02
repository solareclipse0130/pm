const SESSION_KEY = "pm-session-v1";

export type AuthSession = {
  token: string;
  expiresAt: string;
};

export type AuthUser = {
  id: number;
  username: string;
  displayName: string;
  createdAt: string;
  updatedAt: string;
};

export type AuthResult = {
  user: AuthUser;
  session: AuthSession;
};

export class AuthError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "AuthError";
  }
}

const readErrorDetail = async (response: Response): Promise<string> => {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // ignore — non-JSON body
  }
  return response.statusText || `Request failed with status ${response.status}.`;
};

const readSessionFromStorage = (): AuthSession | null => {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as AuthSession;
    if (
      typeof parsed?.token === "string" &&
      typeof parsed?.expiresAt === "string"
    ) {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
};

export const getStoredSession = (): AuthSession | null => {
  const session = readSessionFromStorage();
  if (!session) return null;
  if (new Date(session.expiresAt).getTime() <= Date.now()) {
    clearStoredSession();
    return null;
  }
  return session;
};

export const persistSession = (session: AuthSession): void => {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
};

export const clearStoredSession = (): void => {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(SESSION_KEY);
};

export const authHeaders = (): Record<string, string> => {
  const session = getStoredSession();
  return session ? { Authorization: `Bearer ${session.token}` } : {};
};

export const apiFetch = async (
  input: RequestInfo,
  init: RequestInit = {}
): Promise<Response> => {
  const headers = new Headers(init.headers);
  const session = getStoredSession();
  if (session && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${session.token}`);
  }
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(input, { ...init, headers });
  if (response.status === 401) {
    clearStoredSession();
  }
  return response;
};

export const login = async (
  username: string,
  password: string
): Promise<AuthResult> => {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new AuthError(await readErrorDetail(response), response.status);
  }
  const result = (await response.json()) as AuthResult;
  persistSession(result.session);
  return result;
};

export const signup = async (
  username: string,
  password: string,
  displayName?: string
): Promise<AuthResult> => {
  const response = await fetch("/api/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, displayName }),
  });
  if (!response.ok) {
    throw new AuthError(await readErrorDetail(response), response.status);
  }
  const result = (await response.json()) as AuthResult;
  persistSession(result.session);
  return result;
};

export const fetchCurrentUser = async (): Promise<AuthUser | null> => {
  const session = getStoredSession();
  if (!session) return null;
  const response = await apiFetch("/api/auth/me");
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new AuthError(await readErrorDetail(response), response.status);
  }
  return (await response.json()) as AuthUser;
};

export const logout = async (): Promise<void> => {
  const session = getStoredSession();
  if (!session) return;
  try {
    await apiFetch("/api/auth/logout", { method: "POST" });
  } finally {
    clearStoredSession();
  }
};

export const updateDisplayName = async (
  displayName: string
): Promise<AuthUser> => {
  const response = await apiFetch("/api/auth/profile", {
    method: "PUT",
    body: JSON.stringify({ displayName }),
  });
  if (!response.ok) {
    throw new AuthError(await readErrorDetail(response), response.status);
  }
  return (await response.json()) as AuthUser;
};

export const changePassword = async (
  currentPassword: string,
  newPassword: string
): Promise<void> => {
  const response = await apiFetch("/api/auth/password", {
    method: "PUT",
    body: JSON.stringify({ currentPassword, newPassword }),
  });
  if (!response.ok) {
    throw new AuthError(await readErrorDetail(response), response.status);
  }
};
