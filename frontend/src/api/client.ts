// 100% Offline HTTP Client with Automated CSRF Protection and Network Audit Tracker

interface RequestAuditLog {
  url: string;
  method: string;
  timestamp: string;
  isExternal: boolean;
  status: number;
}

class ApiAuditTracker {
  private logs: RequestAuditLog[] = [];
  private externalCount = 0;

  record(url: string, method: string, status: number) {
    const isExternal = !url.startsWith("/") && !url.startsWith("http://127.0.0.1") && !url.startsWith("http://localhost");
    if (isExternal) {
      this.externalCount++;
    }
    this.logs.unshift({
      url,
      method,
      timestamp: new Date().toISOString(),
      isExternal,
      status,
    });
    if (this.logs.length > 100) {
      this.logs.pop();
    }
  }

  getExternalCount(): number {
    return this.externalCount;
  }

  getLogs(): RequestAuditLog[] {
    return [...this.logs];
  }

  clear() {
    this.logs = [];
    this.externalCount = 0;
  }
}

export const auditTracker = new ApiAuditTracker();

let cachedCsrfToken: string | null = null;

export function setCsrfToken(token: string) {
  cachedCsrfToken = token;
}

export function getCsrfToken(): string | null {
  if (cachedCsrfToken) return cachedCsrfToken;
  const match = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});

  // Automatic CSRF token injection on mutating verbs
  if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
    const token = getCsrfToken();
    if (token && !headers.has("X-CSRF-Token")) {
      headers.set("X-CSRF-Token", token);
    }
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include",
  });

  auditTracker.record(url, method, response.status);

  // Auto-refresh CSRF cookie if returned
  const returnedCsrf = response.headers.get("X-CSRF-Token");
  if (returnedCsrf) {
    cachedCsrfToken = returnedCsrf;
  }

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const rawText = await response.text();
      try {
        const errJson = JSON.parse(rawText);
        errorDetail = errJson.detail || JSON.stringify(errJson);
      } catch {
        errorDetail = rawText || errorDetail;
      }
    } catch {
      // Keep default errorDetail
    }
    throw new Error(errorDetail);
  }

  // Handle empty responses
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return (await response.text()) as unknown as T;
}

export const api = {
  get: <T>(url: string, signal?: AbortSignal) => request<T>(url, { method: "GET", signal }),
  post: <T>(url: string, body?: any, signal?: AbortSignal) => {
    const isFormData = body instanceof FormData;
    return request<T>(url, {
      method: "POST",
      headers: isFormData ? {} : { "Content-Type": "application/json" },
      body: isFormData ? body : JSON.stringify(body),
      signal,
    });
  },
  put: <T>(url: string, body?: any, signal?: AbortSignal) =>
    request<T>(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    }),
  patch: <T>(url: string, body?: any, signal?: AbortSignal) =>
    request<T>(url, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    }),
  delete: <T>(url: string, signal?: AbortSignal) => request<T>(url, { method: "DELETE", signal }),
};
