import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient, { apiErrorMessage } from "../api/client";

export interface AuthUser {
  id: string;
  email: string;
  full_name?: string;
  role: string;
  is_platform_admin: boolean;
  tenant_id?: string | null;
  tenant_slug?: string | null;
  permissions?: string[];
}

interface AuthState {
  user: AuthUser | null;
  loading: boolean;
  error: string | null;
}

function hydrateUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem("user");
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

const initialState: AuthState = { user: hydrateUser(), loading: false, error: null };

export const login = createAsyncThunk(
  "auth/login",
  async (
    credentials: { email: string; password: string; tenant_slug?: string; otp_code?: string },
    { rejectWithValue },
  ) => {
    try {
      const { data } = await apiClient.post("/auth/login", credentials);
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      // Resolve identity so the UI can drive route guards (platform admin vs tenant).
      const me = await apiClient.get("/auth/me");
      localStorage.setItem("user", JSON.stringify(me.data));
      return me.data as AuthUser;
    } catch (err) {
      return rejectWithValue(apiErrorMessage(err, "Login failed"));
    }
  }
);

export const signup = createAsyncThunk(
  "auth/signup",
  async (
    dataObj: { company_name: string; company_slug: string; full_name: string; email: string; password: string },
    { rejectWithValue },
  ) => {
    try {
      const { data } = await apiClient.post("/auth/signup", dataObj);
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      const me = await apiClient.get("/auth/me");
      localStorage.setItem("user", JSON.stringify(me.data));
      return me.data as AuthUser;
    } catch (err) {
      return rejectWithValue(apiErrorMessage(err, "Sign up failed"));
    }
  }
);

export const fetchMe = createAsyncThunk("auth/me", async () => {
  const { data } = await apiClient.get("/auth/me");
  localStorage.setItem("user", JSON.stringify(data));
  return data as AuthUser;
});

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
      .addCase(login.fulfilled, (s, a) => { s.loading = false; s.user = a.payload; })
      .addCase(login.rejected, (s, a) => { s.loading = false; s.error = (a.payload as string) ?? a.error.message ?? "Login failed"; })
      .addCase(signup.pending, (s) => { s.loading = true; s.error = null; })
      .addCase(signup.fulfilled, (s, a) => { s.loading = false; s.user = a.payload; })
      .addCase(signup.rejected, (s, a) => { s.loading = false; s.error = (a.payload as string) ?? a.error.message ?? "Sign up failed"; })
      .addCase(fetchMe.fulfilled, (s, a) => { s.user = a.payload; });
  },
});

export const { logout } = authSlice.actions;
export default authSlice.reducer;
