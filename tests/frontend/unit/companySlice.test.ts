import { describe, it, expect, vi, beforeEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import companyReducer, { fetchCompanies, Company } from "../../../frontend/src/store/companySlice";

vi.mock("../../../frontend/src/api/client", () => ({
  default: {
    get: vi.fn(),
  },
}));
import apiClient from "../../../frontend/src/api/client";

const MOCK_COMPANIES: Company[] = [
  {
    id: "comp-1",
    tenant_id: "tenant-123",
    name: "Acme GST Company",
    gst_status: "GST",
    gstin: "27ABCDE1234F1Z5",
    address: "Mumbai",
    contact_details: {},
    bank_details: {},
    logo_url: null,
    authorized_signatory: {},
    is_default: false,
    is_active: true,
  },
  {
    id: "comp-2",
    tenant_id: "tenant-123",
    name: "Acme Non-GST Company",
    gst_status: "NON_GST",
    gstin: null,
    address: "Pune",
    contact_details: {},
    bank_details: {},
    logo_url: null,
    authorized_signatory: {},
    is_default: true,
    is_active: true,
  },
];

function makeStore() {
  return configureStore({ reducer: { company: companyReducer } });
}

describe("companySlice — initial state", () => {
  it("starts with empty list, defaultCompany as null, loading=false, error=null", () => {
    const state = makeStore().getState().company;
    expect(state.list).toEqual([]);
    expect(state.defaultCompany).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });
});

describe("companySlice — fetchCompanies", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sets loading=true, error=null on pending", () => {
    const store = makeStore();
    store.dispatch(fetchCompanies());
    const state = store.getState().company;
    expect(state.loading).toBe(true);
    expect(state.error).toBeNull();
  });

  it("populates list and defaultCompany on fulfilled", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: MOCK_COMPANIES });
    const store = makeStore();
    await store.dispatch(fetchCompanies());
    const state = store.getState().company;
    
    expect(state.loading).toBe(false);
    expect(state.list).toHaveLength(2);
    expect(state.list[0].name).toBe("Acme GST Company");
    expect(state.defaultCompany).toEqual(MOCK_COMPANIES[1]); // comp-2 is default and active
  });

  it("sets loading=false and error message on rejected", async () => {
    (apiClient.get as any).mockRejectedValueOnce({
      response: { data: { detail: "Auth error or server down" } },
    });
    const store = makeStore();
    await store.dispatch(fetchCompanies());
    const state = store.getState().company;

    expect(state.loading).toBe(false);
    expect(state.error).toBe("Auth error or server down");
    expect(state.list).toEqual([]);
    expect(state.defaultCompany).toBeNull();
  });

  it("sets fallback error if reject payload has no detail", async () => {
    (apiClient.get as any).mockRejectedValueOnce(new Error("Generic Network Error"));
    const store = makeStore();
    await store.dispatch(fetchCompanies());
    const state = store.getState().company;

    expect(state.loading).toBe(false);
    expect(state.error).toBe("Failed to fetch companies");
  });

  it("calls GET /companies", async () => {
    (apiClient.get as any).mockResolvedValueOnce({ data: [] });
    await makeStore().dispatch(fetchCompanies());
    expect(apiClient.get).toHaveBeenCalledWith("/companies");
  });
});
