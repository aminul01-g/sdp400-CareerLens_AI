/**
 * Typed HTTP client.
 *
 * Wraps `fetch` with three things every call site would otherwise repeat:
 * the bearer token, JSON (or FormData) handling, and normalisation of a failed
 * response into an `ApiError` carrying the status and the parsed envelope.
 */
import { API_BASE_URL, API_PREFIX, ApiError, type ApiErrorEnvelope } from "./config";
import { getToken } from "@/lib/auth/session";

type Method = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export interface RequestOptions {
  method?: Method;
  /** JSON body. Mutually exclusive with `formData`. */
  body?: unknown;
  /** Multipart body. The browser must set the boundary, so no Content-Type. */
  formData?: FormData;
  /** Query parameters. `undefined` and `null` values are dropped. */
  query?: Record<string, string | number | boolean | undefined | null>;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const base = path.startsWith(API_PREFIX) || path.startsWith("http")
    ? path
    : `${API_PREFIX}${path.startsWith("/") ? path : `/${path}`}`;
  const url = base.startsWith("http") ? base : `${API_BASE_URL}${base}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") {
      params.append(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

async function toApiError(response: Response): Promise<ApiError> {
  let payload: unknown;
  let message = `Request failed with status ${response.status}`;
  try {
    const text = await response.text();
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        // A non-JSON body (an HTML error page, a proxy timeout) must still
        // produce a usable message rather than a parse exception.
        message = text.slice(0, 300);
      }
    }
  } catch {
    /* keep the default message */
  }
  const envelope = payload as ApiErrorEnvelope | undefined;
  if (envelope?.error?.message) message = envelope.error.message;
  else if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    message = typeof detail === "string" ? detail : message;
  }
  return new ApiError(response.status, message, payload);
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, formData, query, signal } = options;
  const headers: Record<string, string> = { Accept: "application/json" };

  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload: BodyInit | undefined;
  if (formData) {
    payload = formData; // fetch sets the multipart boundary itself
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const response = await fetch(buildUrl(path, query), {
    method,
    headers,
    body: payload,
    signal,
  });

  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;

  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export const apiFetch = {
  get: <T>(path: string, query?: RequestOptions["query"], signal?: AbortSignal) =>
    request<T>(path, { method: "GET", query, signal }),
  post: <T>(path: string, body?: unknown, query?: RequestOptions["query"]) =>
    request<T>(path, { method: "POST", body, query }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, formData: FormData) => request<T>(path, { method: "POST", formData }),
};

/** A user-visible message for any thrown value. */
export function errorMessage(error: unknown, fallback = "Something went wrong."): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return fallback;
}
