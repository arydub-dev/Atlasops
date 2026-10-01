// Resolution order:
//  1. Explicit NEXT_PUBLIC_API_URL (e.g. a separate backend host on Render).
//  2. Local development -> the backend dev server on :8000.
//  3. Production with no explicit URL -> same-origin ("" base), so requests go
//     to "/api/v1/..." on the current domain. This is how the all-in-one Vercel
//     deployment works, where the FastAPI service is mounted under "/api".
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "");

const API_PREFIX = "/api/v1";

const ORG_KEY = "supply_org_id";

export function getOrgId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ORG_KEY);
}

export function setOrgId(orgId: string) {
  if (typeof window !== "undefined") window.localStorage.setItem(ORG_KEY, orgId);
}

export function clearOrgId() {
  if (typeof window !== "undefined") window.localStorage.removeItem(ORG_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  auth?: boolean;
}

function orgHeaders(): Record<string, string> {
  const orgId = getOrgId();
  return orgId ? { "X-Organization-Id": orgId } : {};
}

function shouldRedirectOn401(): boolean {
  if (typeof window === "undefined") return false;
  const path = window.location.pathname;
  // Stay put on public / auth / onboarding surfaces — /auth/me 401 is expected there.
  if (
    path === "/" ||
    path.startsWith("/login") ||
    path.startsWith("/auth/") ||
    path.startsWith("/invite/") ||
    path.startsWith("/onboarding") ||
    path.startsWith("/get-started") ||
    path.startsWith("/platform") ||
    path.startsWith("/solutions") ||
    path.startsWith("/pricing") ||
    path.startsWith("/product") ||
    path.startsWith("/company") ||
    path.startsWith("/legal") ||
    path.startsWith("/blog") ||
    path.startsWith("/docs") ||
    path.startsWith("/contact") ||
    path.startsWith("/security") ||
    path.startsWith("/about") ||
    path.startsWith("/integrations")
  ) {
    return false;
  }
  return true;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, auth = true, headers, ...rest } = options;
  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(headers as Record<string, string>),
  };
  if (auth) {
    Object.assign(finalHeaders, orgHeaders());
  }

  const res = await fetch(`${API_BASE}${API_PREFIX}${path}`, {
    ...rest,
    headers: finalHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: "include",
    cache: "no-store",
  });

  if (res.status === 401 && typeof window !== "undefined") {
    clearOrgId();
    if (shouldRedirectOn401()) {
      // Centralized fetch helpers live outside React components, so router hooks
      // are unavailable here. A hard redirect is the safest fallback on 401.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/login";
    }
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : "Request failed");
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

async function uploadRequest<T>(path: string, formData: FormData): Promise<T> {
  const headers: Record<string, string> = { ...orgHeaders() };

  const res = await fetch(`${API_BASE}${API_PREFIX}${path}`, {
    method: "POST",
    headers, // do NOT set Content-Type; browser sets multipart boundary
    body: formData,
    credentials: "include",
    cache: "no-store",
  });

  if (res.status === 401 && typeof window !== "undefined") {
    clearOrgId();
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    if (shouldRedirectOn401()) window.location.href = "/login";
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : "Upload failed");
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, formData: FormData) => uploadRequest<T>(path, formData),
};

export { API_BASE };
