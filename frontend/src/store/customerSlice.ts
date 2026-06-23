import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient, { apiErrorMessage } from "../api/client";

interface Customer {
  id: string;
  name: string;
  category: string;
  status?: string;
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

export const createCustomer = createAsyncThunk(
  "customers/create",
  async (payload: Omit<Customer, "id">, { rejectWithValue }) => {
    try {
      const { data } = await apiClient.post("/customers", payload);
      return data as Customer;
    } catch (err) {
      return rejectWithValue(apiErrorMessage(err, "Failed to create customer"));
    }
  },
);

export const updateCustomer = createAsyncThunk(
  "customers/update",
  async ({ id, changes }: { id: string; changes: Partial<Customer> }, { rejectWithValue }) => {
    try {
      const { data } = await apiClient.patch(`/customers/${id}`, changes);
      return data as Customer;
    } catch (err) {
      return rejectWithValue(apiErrorMessage(err, "Failed to update customer"));
    }
  },
);

const customerSlice = createSlice({
  name: "customers",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchCustomers.pending, (s) => { s.loading = true; })
      .addCase(fetchCustomers.fulfilled, (s, a) => { s.loading = false; s.items = a.payload; })
      .addCase(fetchCustomers.rejected, (s, a) => { s.loading = false; s.error = a.error.message ?? null; })
      .addCase(createCustomer.fulfilled, (s, a) => { s.items.push(a.payload); })
      .addCase(updateCustomer.fulfilled, (s, a) => {
        const i = s.items.findIndex(c => c.id === a.payload.id);
        if (i !== -1) s.items[i] = a.payload;
      });
  },
});

export default customerSlice.reducer;
