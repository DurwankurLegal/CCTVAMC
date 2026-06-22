import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "../api/client";

interface Customer {
  id: string;
  name: string;
  category: string;
  phone?: string;
  email?: string;
  is_active: boolean;
}

interface State { items: Customer[]; loading: boolean; error: string | null }
const initialState: State = { items: [], loading: false, error: null };

export const fetchCustomers = createAsyncThunk("customers/list", async () => {
  const { data } = await apiClient.get("/customers");
  return data as Customer[];
});

export const createCustomer = createAsyncThunk("customers/create", async (payload: Omit<Customer, "id">) => {
  const { data } = await apiClient.post("/customers", payload);
  return data as Customer;
});

const customerSlice = createSlice({
  name: "customers",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchCustomers.pending, (s) => { s.loading = true; })
      .addCase(fetchCustomers.fulfilled, (s, a) => { s.loading = false; s.items = a.payload; })
      .addCase(fetchCustomers.rejected, (s, a) => { s.loading = false; s.error = a.error.message ?? null; })
      .addCase(createCustomer.fulfilled, (s, a) => { s.items.push(a.payload); });
  },
});

export default customerSlice.reducer;
