import axios from "axios";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  headers: { "Content-Type": "application/json" },
});

// Attach JWT token from localStorage on every request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401, attempt a one-shot token refresh; on failure, redirect to login.
// IMPORTANT: never refresh/retry the auth endpoints themselves — a 401 from
// /auth/login (wrong password) must surface to the caller, not be retried, or a
// stale-but-valid refresh token causes an infinite login↔refresh loop.
apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config ?? {};
    const url: string = original.url ?? "";
    const isAuthEndpoint = url.includes("/auth/login") || url.includes("/auth/refresh");

    if (error.response?.status === 401 && !isAuthEndpoint && !original._retry) {
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        original._retry = true; // retry a given request at most once
        try {
          const { data } = await axios.post("/api/v1/auth/refresh", { refresh_token: refreshToken });
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);
          original.headers = original.headers ?? {};
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return apiClient.request(original);
        } catch {
          localStorage.clear();
          window.location.href = "/login";
        }
      } else {
        localStorage.clear();
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Turn an axios error into a human-readable message, unpacking FastAPI's
 * validation payloads ({detail: "..."} or {detail: [{loc, msg}, ...]}).
 */
export function apiErrorMessage(err: any, fallback = "Something went wrong"): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: any) => {
        const field = Array.isArray(d?.loc) ? d.loc[d.loc.length - 1] : undefined;
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .join("; ");
  }
  return err?.message || fallback;
}

export default apiClient;
