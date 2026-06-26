import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "../api/client";

export interface Company {
  id: string;
  tenant_id: string;
  name: string;
  gst_status: string;
  gstin: string | null;
  address: string | null;
  contact_details: Record<string, any>;
  bank_details: Record<string, any>;
  logo_url: string | null;
  authorized_signatory: Record<string, any>;
  is_default: boolean;
  is_active: boolean;
}

interface CompanyState {
  list: Company[];
  defaultCompany: Company | null;
  loading: boolean;
  error: string | null;
}

const initialState: CompanyState = {
  list: [],
  defaultCompany: null,
  loading: false,
  error: null,
};

export const fetchCompanies = createAsyncThunk(
  "company/fetchList",
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await apiClient.get<Company[]>("/companies");
      return data;
    } catch (err: any) {
      return rejectWithValue(
        err.response?.data?.detail || "Failed to fetch companies"
      );
    }
  }
);

const companySlice = createSlice({
  name: "company",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchCompanies.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCompanies.fulfilled, (state, action) => {
        state.loading = false;
        state.list = action.payload;
        state.defaultCompany = action.payload.find((c) => c.is_default && c.is_active) || null;
      })
      .addCase(fetchCompanies.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export default companySlice.reducer;
