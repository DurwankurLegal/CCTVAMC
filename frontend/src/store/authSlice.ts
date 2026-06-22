import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import apiClient from "../api/client";

interface AuthState {
  user: { id: string; email: string; role: string } | null;
  loading: boolean;
  error: string | null;
}

const initialState: AuthState = { user: null, loading: false, error: null };

export const login = createAsyncThunk(
  "auth/login",
  async (credentials: { email: string; password: string }) => {
    const { data } = await apiClient.post("/auth/login", credentials);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    return data;
  }
);

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    logout(state) {
      state.user = null;
      localStorage.clear();
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (s) => { s.loading = true; s.error = null; })
      .addCase(login.fulfilled, (s, a) => { s.loading = false; })
      .addCase(login.rejected, (s, a) => { s.loading = false; s.error = a.error.message ?? "Login failed"; });
  },
});

export const { logout } = authSlice.actions;
export default authSlice.reducer;
