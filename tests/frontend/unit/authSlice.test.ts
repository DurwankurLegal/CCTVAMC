/**
 * Unit tests — authSlice (Redux)
 * ================================
 * Covers: login thunk (pending/fulfilled/rejected), fetchMe,
 *         logout action, hydrateUser from localStorage,
 *         initial state, error clearing.
 *
 * Run: cd frontend && npm test
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import authReducer, {
  login,
  fetchMe,
  logout,
  type AuthUser,
} from "../../../frontend/src/store/authSlice";

// ── Mock apiClient ──────────────────────────────────────────────────────────
vi.mock("../../../frontend/src/api/client", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
  apiErrorMessage: (err: any, fallback = "error") =>
    err?.response?.data?.detail ?? err?.message ?? fallback,
}));
import apiClient from "../../../frontend/src/api/client";

// ── Helpers ─────────────────────────────────────────────────────────────────

const MOCK_USER: AuthUser = {
  id: "user-1",
  email: "admin@acme.com",
  full_name: "Admin User",
  role: "admin",
  is_platform_admin: false,
  tenant_id: "tenant-1",
  permissions: ["customers:read", "invoices:read"],
};

const MOCK_TOKENS = {
  access_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
  refresh_token: "refresh.token.here",
};

function makeStore() {
  return configureStore({ reducer: { auth: authReducer } });
}

// ── Initial state ────────────────────────────────────────────────────────────

describe("authSlice — initial state", () => {
  beforeEach(() => localStorage.clear());

  it("has null user when localStorage is empty", () => {
    const store = makeStore();
    expect(store.getState().auth.user).toBeNull();
  });

  it("hydrates user from localStorage if present", async () => {
    // initialState calls hydrateUser() once at module load, so seed storage
    // first and re-import the module to recompute the initial state.
    localStorage.setItem("user", JSON.stringify(MOCK_USER));
    vi.resetModules();
    const freshReducer = (await import("../../../frontend/src/store/authSlice")).default;
    const store = configureStore({ reducer: { auth: freshReducer } });
    expect(store.getState().auth.user?.email).toBe("admin@acme.com");
  });

  it("has loading=false initially", () => {
    const store = makeStore();
    expect(store.getState().auth.loading).toBe(false);
  });

  it("has error=null initially", () => {
    const store = makeStore();
    expect(store.getState().auth.error).toBeNull();
  });
});

// ── login thunk ───────────────────────────────────────────────────────────────

describe("authSlice — login thunk", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("sets loading=true on pending", () => {
    const store = makeStore();
    store.dispatch(login({ email: "x", password: "y" }));
    expect(store.getState().auth.loading).toBe(true);
  });

  it("sets user and loading=false on fulfilled", async () => {
    (apiClient.post as any).mockResolvedValueOnce({ data: MOCK_TOKENS });
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_USER });
    const store = makeStore();
    await store.dispatch(login({ email: "admin@acme.com", password: "pass" }));
    const state = store.getState().auth;
    expect(state.loading).toBe(false);
    expect(state.user?.email).toBe("admin@acme.com");
  });

  it("stores access_token in localStorage on success", async () => {
    (apiClient.post as any).mockResolvedValueOnce({ data: MOCK_TOKENS });
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_USER });
    const store = makeStore();
    await store.dispatch(login({ email: "a", password: "b" }));
    expect(localStorage.getItem("access_token")).toBe(MOCK_TOKENS.access_token);
  });

  it("stores refresh_token in localStorage on success", async () => {
    (apiClient.post as any).mockResolvedValueOnce({ data: MOCK_TOKENS });
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_USER });
    const store = makeStore();
    await store.dispatch(login({ email: "a", password: "b" }));
    expect(localStorage.getItem("refresh_token")).toBe(MOCK_TOKENS.refresh_token);
  });

  it("sets error message on rejected", async () => {
    (apiClient.post as any).mockRejectedValueOnce(new Error("Invalid credentials"));
    const store = makeStore();
    await store.dispatch(login({ email: "a", password: "bad" }));
    const state = store.getState().auth;
    expect(state.loading).toBe(false);
    expect(state.error).toBe("Invalid credentials");
    expect(state.user).toBeNull();
  });

  it("includes tenant_slug in the request when provided", async () => {
    (apiClient.post as any).mockResolvedValueOnce({ data: MOCK_TOKENS });
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_USER });
    await makeStore().dispatch(
      login({ email: "a", password: "b", tenant_slug: "acme-security" })
    );
    expect(apiClient.post).toHaveBeenCalledWith("/auth/login", {
      email: "a",
      password: "b",
      tenant_slug: "acme-security",
    });
  });
});

// ── fetchMe thunk ─────────────────────────────────────────────────────────────

describe("authSlice — fetchMe thunk", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("updates user on fulfilled", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_USER });
    const store = makeStore();
    await store.dispatch(fetchMe());
    expect(store.getState().auth.user?.email).toBe("admin@acme.com");
  });

  it("caches user in localStorage on fulfilled", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_USER });
    const store = makeStore();
    await store.dispatch(fetchMe());
    const cached = JSON.parse(localStorage.getItem("user") ?? "null");
    expect(cached?.id).toBe("user-1");
  });
});

// ── logout action ─────────────────────────────────────────────────────────────

describe("authSlice — logout", () => {
  it("clears user from state", () => {
    localStorage.setItem("user", JSON.stringify(MOCK_USER));
    const store = makeStore();
    store.dispatch(logout());
    expect(store.getState().auth.user).toBeNull();
  });

  it("clears localStorage", () => {
    localStorage.setItem("access_token", "tok");
    localStorage.setItem("user", JSON.stringify(MOCK_USER));
    const store = makeStore();
    store.dispatch(logout());
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("user")).toBeNull();
  });
});
