import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "../api/client";

export interface TenantConfig {
  resolved: boolean;
  id?: string;
  name: string;
  slug: string;
  branding: {
    primary_color: string;
    logo_url: string | null;
  };
}

interface TenantState {
  config: TenantConfig | null;
  loading: boolean;
  error: string | null;
}

const initialState: TenantState = {
  config: null,
  loading: false,
  error: null,
};

export const fetchTenantConfig = createAsyncThunk(
  "tenant/fetchConfig",
  async (host: string, { rejectWithValue }) => {
    try {
      // Pass the hostname explicitly so backend resolves correctly in all dev environments
      const { data } = await apiClient.get<TenantConfig>(`/tenants/config`, {
        params: { host },
      });
      return data;
    } catch (err: any) {
      return rejectWithValue(
        err.response?.data?.detail || "Failed to resolve tenant config"
      );
    }
  }
);

const tenantSlice = createSlice({
  name: "tenant",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchTenantConfig.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchTenantConfig.fulfilled, (state, action) => {
        state.loading = false;
        state.config = action.payload;
        if (action.payload.resolved) {
          document.title = `${action.payload.name} CCTV AMC`;
        }
      })
      .addCase(fetchTenantConfig.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export default tenantSlice.reducer;
