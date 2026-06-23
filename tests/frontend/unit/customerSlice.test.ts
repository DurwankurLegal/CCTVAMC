/**
 * Unit tests — customerSlice (Redux)
 * =====================================
 * Covers: fetchCustomers (pending/fulfilled/rejected),
 *         createCustomer, updateCustomer, initial state.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import customerReducer, {
  fetchCustomers,
  createCustomer,
  updateCustomer,
} from "../../../frontend/src/store/customerSlice";

vi.mock("../../../frontend/src/api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  apiErrorMessage: (err: any, fallback = "error") =>
    err?.response?.data?.detail ?? err?.message ?? fallback,
}));
import apiClient from "../../../frontend/src/api/client";

const MOCK_CUSTOMERS = [
  { id: "c1", name: "Sunrise CHS", category: "chs", is_active: true },
  { id: "c2", name: "Raj Stores",  category: "single_shop", is_active: true },
];

function makeStore() {
  return configureStore({ reducer: { customers: customerReducer } });
}

// ── Initial state ────────────────────────────────────────────────────────────

describe("customerSlice — initial state", () => {
  it("starts with empty items array", () => {
    expect(makeStore().getState().customers.items).toEqual([]);
  });

  it("starts with loading=false", () => {
    expect(makeStore().getState().customers.loading).toBe(false);
  });

  it("starts with error=null", () => {
    expect(makeStore().getState().customers.error).toBeNull();
  });
});

// ── fetchCustomers ────────────────────────────────────────────────────────────

describe("customerSlice — fetchCustomers", () => {
  beforeEach(() => vi.clearAllMocks());

  it("sets loading=true on pending", () => {
    const store = makeStore();
    store.dispatch(fetchCustomers());
    expect(store.getState().customers.loading).toBe(true);
  });

  it("populates items on fulfilled", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_CUSTOMERS });
    const store = makeStore();
    await store.dispatch(fetchCustomers());
    expect(store.getState().customers.items).toHaveLength(2);
    expect(store.getState().customers.items[0].name).toBe("Sunrise CHS");
  });

  it("sets loading=false after fulfilled", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_CUSTOMERS });
    const store = makeStore();
    await store.dispatch(fetchCustomers());
    expect(store.getState().customers.loading).toBe(false);
  });

  it("sets error on rejected", async () => {
    (apiClient.get as any).mockRejectedValueOnce(new Error("Network error"));
    const store = makeStore();
    await store.dispatch(fetchCustomers());
    expect(store.getState().customers.error).toBe("Network error");
    expect(store.getState().customers.loading).toBe(false);
  });

  it("calls GET /customers", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: [] });
    await makeStore().dispatch(fetchCustomers());
    expect(apiClient.get).toHaveBeenCalledWith("/customers");
  });
});

// ── createCustomer ────────────────────────────────────────────────────────────

describe("customerSlice — createCustomer", () => {
  beforeEach(() => vi.clearAllMocks());

  it("adds new customer to items on fulfilled", async () => {
    const newCustomer = { id: "c3", name: "New Corp", category: "commercial", is_active: true };
    (apiClient.post as any).mockResolvedValueOnce({ data: newCustomer });

    const store = makeStore();
    await store.dispatch(createCustomer({ name: "New Corp", category: "commercial", is_active: true }));
    expect(store.getState().customers.items).toHaveLength(1);
    expect(store.getState().customers.items[0].id).toBe("c3");
  });

  it("calls POST /customers with payload", async () => {
    const payload = { name: "Corp", category: "commercial", is_active: true };
    (apiClient.post as any).mockResolvedValueOnce({ data: { id: "c4", ...payload } });
    await makeStore().dispatch(createCustomer(payload));
    expect(apiClient.post).toHaveBeenCalledWith("/customers", payload);
  });
});

// ── updateCustomer ────────────────────────────────────────────────────────────

describe("customerSlice — updateCustomer", () => {
  beforeEach(() => vi.clearAllMocks());

  it("updates existing customer in items on fulfilled", async () => {
    // Pre-populate store
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_CUSTOMERS });
    const store = makeStore();
    await store.dispatch(fetchCustomers());

    const updated = { ...MOCK_CUSTOMERS[0], name: "Updated Name" };
    (apiClient.patch as any).mockResolvedValueOnce({ data: updated });
    await store.dispatch(updateCustomer({ id: "c1", changes: { name: "Updated Name" } }));

    const found = store.getState().customers.items.find((c) => c.id === "c1");
    expect(found?.name).toBe("Updated Name");
  });

  it("does not change other customers on update", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_CUSTOMERS });
    const store = makeStore();
    await store.dispatch(fetchCustomers());

    const updated = { ...MOCK_CUSTOMERS[0], name: "Changed" };
    (apiClient.patch as any).mockResolvedValueOnce({ data: updated });
    await store.dispatch(updateCustomer({ id: "c1", changes: { name: "Changed" } }));

    expect(store.getState().customers.items[1].name).toBe("Raj Stores");
  });

  it("calls PATCH /customers/:id with changes", async () => {
    (apiClient.patch as any).mockResolvedValueOnce({
      data: { id: "c1", name: "X", category: "chs", is_active: true },
    });
    await makeStore().dispatch(updateCustomer({ id: "c1", changes: { name: "X" } }));
    expect(apiClient.patch).toHaveBeenCalledWith("/customers/c1", { name: "X" });
  });
});
