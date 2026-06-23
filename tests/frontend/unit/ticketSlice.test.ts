/**
 * Unit tests — ticketSlice (Redux)
 * ==================================
 * Covers: fetchTickets (pending/fulfilled/rejected), initial state.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import ticketReducer, { fetchTickets } from "../../../frontend/src/store/ticketSlice";

vi.mock("../../../frontend/src/api/client", () => ({
  default: { get: vi.fn() },
}));
import apiClient from "../../../frontend/src/api/client";

const MOCK_TICKETS = [
  {
    id: "t1",
    ticket_number: "TKT-2026-00001",
    customer_id: "c1",
    status: "open",
    priority: "high",
    complaint: "Camera offline",
    sla_breached: false,
  },
  {
    id: "t2",
    ticket_number: "TKT-2026-00002",
    customer_id: "c2",
    status: "in_progress",
    priority: "critical",
    complaint: "DVR not recording",
    sla_breached: true,
  },
];

function makeStore() {
  return configureStore({ reducer: { tickets: ticketReducer } });
}

// ── Initial state ─────────────────────────────────────────────────────────────

describe("ticketSlice — initial state", () => {
  it("starts with empty items", () => {
    expect(makeStore().getState().tickets.items).toEqual([]);
  });

  it("starts with loading=false", () => {
    expect(makeStore().getState().tickets.loading).toBe(false);
  });

  it("starts with error=null", () => {
    expect(makeStore().getState().tickets.error).toBeNull();
  });
});

// ── fetchTickets ──────────────────────────────────────────────────────────────

describe("ticketSlice — fetchTickets", () => {
  beforeEach(() => vi.clearAllMocks());

  it("sets loading=true on pending", () => {
    const store = makeStore();
    store.dispatch(fetchTickets());
    expect(store.getState().tickets.loading).toBe(true);
  });

  it("populates items on fulfilled", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_TICKETS });
    const store = makeStore();
    await store.dispatch(fetchTickets());
    expect(store.getState().tickets.items).toHaveLength(2);
  });

  it("sets loading=false after fulfilled", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_TICKETS });
    const store = makeStore();
    await store.dispatch(fetchTickets());
    expect(store.getState().tickets.loading).toBe(false);
  });

  it("maps ticket fields correctly", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_TICKETS });
    const store = makeStore();
    await store.dispatch(fetchTickets());
    const t = store.getState().tickets.items[0];
    expect(t.ticket_number).toBe("TKT-2026-00001");
    expect(t.priority).toBe("high");
    expect(t.sla_breached).toBe(false);
  });

  it("sla_breached=true preserved for critical tickets", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_TICKETS });
    const store = makeStore();
    await store.dispatch(fetchTickets());
    const t = store.getState().tickets.items[1];
    expect(t.sla_breached).toBe(true);
  });

  it("sets error on rejected", async () => {
    (apiClient.get as any).mockRejectedValueOnce(new Error("API error"));
    const store = makeStore();
    await store.dispatch(fetchTickets());
    expect(store.getState().tickets.error).toBe("API error");
    expect(store.getState().tickets.loading).toBe(false);
  });

  it("calls GET /service-tickets", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: [] });
    await makeStore().dispatch(fetchTickets());
    expect(apiClient.get).toHaveBeenCalledWith("/service-tickets");
  });

  it("replaces previous items on each fetch", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_TICKETS });
    const store = makeStore();
    await store.dispatch(fetchTickets());
    expect(store.getState().tickets.items).toHaveLength(2);

    (apiClient.get as any).mockResolvedValueOnce({ data: [MOCK_TICKETS[0]] });
    await store.dispatch(fetchTickets());
    expect(store.getState().tickets.items).toHaveLength(1);
  });

  it("returns empty array when API returns empty", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: [] });
    const store = makeStore();
    await store.dispatch(fetchTickets());
    expect(store.getState().tickets.items).toEqual([]);
  });
});
