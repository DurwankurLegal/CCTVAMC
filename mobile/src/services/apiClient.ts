import axios from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";

const BASE_URL = "https://api.cctvplatform.in/api/v1"; // Replace with actual URL

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        const refreshToken = await AsyncStorage.getItem("refresh_token");
        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        await AsyncStorage.setItem("access_token", data.access_token);
        await AsyncStorage.setItem("refresh_token", data.refresh_token);
        error.config.headers.Authorization = `Bearer ${data.access_token}`;
        return apiClient.request(error.config);
      } catch {
        await AsyncStorage.clear();
        // Navigate to login — handled by NavigationRef
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
