/**
 * Shared API client for the real backend (`/api/v1`).
 *
 * Contract notes:
 * - Bearer-token session auth (see app/core/security.py).
 * - Errors are `{detail: string}`; 401 means the session is expired/revoked.
 * - The token lives in sessionStorage only (cleared when the tab closes);
 *   it is never placed in query strings and never logged.
 * - No silent fallbacks: any failure surfaces as a real error state.
 */

/** Base URL for the API. Override with VITE_API_BASE_URL (no trailing slash needed). */
const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
const API_PREFIX = `${API_ORIGIN}/api/v1`;
const TOKEN_KEY = "mais.session";
export const UNAUTHORIZED_EVENT = "mais:unauthorized";

export class ApiError extends Error {
  status: number;
  /** Server-provided safe detail. Never contains stack traces by contract. */
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** The bearer token. sessionStorage keeps it out of long-lived storage and clears on tab close. */
export function getToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* storage unavailable (privacy mode): session works for this page only */
  }
}

export function clearToken(): void {
  try {
    sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

interface RequestOptions<TBody = unknown> {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: TBody;
  /** Raw body for multipart uploads (already built FormData). */
  form?: FormData;
  timeoutMs?: number;
  signal?: AbortSignal;
}

function safeDetail(detail: unknown, status: number): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  // FastAPI validation errors arrive as arrays of objects; summarize without
  // echoing internal schema internals verbatim.
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string; loc?: unknown[] };
    const field = Array.isArray(first.loc)
      ? String(first.loc[first.loc.length - 1])
      : "";
    if (first.msg) return field ? `Invalid value for "${field}": ${first.msg}` : first.msg;
  }
  if (status === 401) return "Your session has expired. Please log in again.";
  if (status === 403) return "You do not have permission to perform this action.";
  if (status === 404) return "The requested resource was not found.";
  if (status === 413) return "The request payload is too large.";
  if (status === 422) return "Validation failed for this request.";
  if (status === 429) return "Too many requests. Please wait and try again.";
  if (status >= 500) return "The server encountered an error. Please retry.";
  return `Request failed (HTTP ${status}).`;
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, form, timeoutMs = 30_000, signal } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const onOuterAbort = () => controller.abort();
  signal?.addEventListener("abort", onOuterAbort);

  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  try {
    const response = await fetch(`${API_PREFIX}${path}`, {
      method,
      headers,
      body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
      signal: controller.signal,
    });
    let payload: unknown = null;
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
    }
    if (!response.ok) {
      const detail = safeDetail(
        payload && typeof payload === "object" && "detail" in payload
          ? (payload as { detail: unknown }).detail
          : null,
        response.status,
      );
      if (response.status === 401) {
        clearToken();
        window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
      }
      throw new ApiError(response.status, detail);
    }
    if (payload === null) {
      // Non-JSON success body (e.g. report export). Return the response for
      // callers that need the raw content via the blob helper below.
      throw new ApiError(response.status, "Unexpected empty JSON response");
    }
    return payload as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      if (signal?.aborted) throw error; // caller cancellation — rethrow silently
      throw new ApiError(0, "The request timed out. Please try again.");
    }
    throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onOuterAbort);
  }
}

/** Download a non-JSON payload (report export) as text with auth attached. */
export async function requestText(path: string): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30_000);
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  try {
    const response = await fetch(`${API_PREFIX}${path}`, {
      headers,
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new ApiError(response.status, safeDetail(null, response.status));
    }
    return await response.text();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, "The download failed. Please try again.");
  } finally {
    clearTimeout(timer);
  }
}
