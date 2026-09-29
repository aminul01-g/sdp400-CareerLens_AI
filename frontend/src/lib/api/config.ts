/**
 * API base URL and shared client primitives.
 *
 * `NEXT_PUBLIC_API_URL` is inlined at build time, which replaces the Vite-only
 * `import.meta.env.VITE_API_BASE_URL` the predecessor client used. The plan
 * resolves the old `.env` / `.env.development` conflict (which disagreed on
 * ports 5001 vs 5000) by having exactly one variable, documented in
 * `.env.example`, defaulting to the backend's documented local port.
 */
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

export const API_PREFIX = "/api";

/** The uniform error envelope every endpoint returns. */
export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    errors?: { field: string; message: string }[];
  };
}

/**
 * A failed API call.
 *
 * Carries `status` and the parsed body, which is the error-enrichment pattern
 * the predecessor client already used (`client.ts:20-29`) and which the UI needs:
 * a 409 is a toast, a 422 is a per-field form error, and a 401 is a redirect to
 * login. Those three cannot be handled without the status.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly body: unknown;
  readonly fieldErrors: Record<string, string>;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    const envelope = body as ApiErrorEnvelope | undefined;
    this.code = envelope?.error?.code ?? `http_${status}`;
    const fieldErrors: Record<string, string> = {};
    for (const item of envelope?.error?.errors ?? []) {
      // First error per field wins: Pydantic can report several for one field,
      // and showing all of them at once is noise.
      fieldErrors[item.field] ??= item.message;
    }
    this.fieldErrors = fieldErrors;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }

  get isValidation(): boolean {
    return this.status === 422;
  }
}

export const TOKEN_KEY = "careerlens_token";
export const USER_KEY = "careerlens_user";

/**
 * Cookie names, shared with `src/middleware.ts` and the server-side layouts.
 *
 * The session is dual-written: localStorage for the fetch client, cookies so Edge
 * middleware and the React server components can see it. See
 * `src/lib/auth/session.ts` for why both.
 */
export const TOKEN_COOKIE = "careerlens_token";
export const USER_COOKIE = "careerlens_user";
