import axios from "axios";
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "./secureStorage";

const BASE_URL = "https://api.cctvplatform.in/api/v1"; // Replace with actual URL

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use(async (config) => {
  const token = await getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        const refreshToken = await getRefreshToken();
        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        await setTokens(data.access_token, data.refresh_token);
        error.config.headers.Authorization = `Bearer ${data.access_token}`;
        return apiClient.request(error.config);
      } catch {
        await clearTokens();
        // Navigate to login — handled by NavigationRef
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
