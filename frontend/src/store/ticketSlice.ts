import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "../api/client";

interface Ticket {
  id: string;
  ticket_number: string;
  customer_id: string;
  status: string;
  priority: string;
  complaint: string;
  sla_breached: boolean;
}

interface State { items: Ticket[]; loading: boolean; error: string | null }
const initialState: State = { items: [], loading: false, error: null };

export const fetchTickets = createAsyncThunk("tickets/list", async () => {
  const { data } = await apiClient.get("/service-tickets");
  return data as Ticket[];
});

const ticketSlice = createSlice({
  name: "tickets",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchTickets.pending, (s) => { s.loading = true; })
      .addCase(fetchTickets.fulfilled, (s, a) => { s.loading = false; s.items = a.payload; })
      .addCase(fetchTickets.rejected, (s, a) => { s.loading = false; s.error = a.error.message ?? null; });
  },
});

export default ticketSlice.reducer;
