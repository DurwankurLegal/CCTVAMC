import axios from "axios";

// Dedicated client for the customer self-service portal. Kept separate from the
// staff apiClient so portal tokens (scope=portal) never mix with staff tokens.
const base = import.meta.env.VITE_API_BASE_URL || "/api/v1";

const portalClient = axios.create({
  baseURL: `${base}/portal`,
  headers: { "Content-Type": "application/json" },
});

portalClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("portal_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

portalClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      const refresh = localStorage.getItem("portal_refresh");
      if (refresh) {
        try {
          const { data } = await axios.post(`${base}/portal/refresh`, { refresh_token: refresh });
          localStorage.setItem("portal_token", data.access_token);
          localStorage.setItem("portal_refresh", data.refresh_token);
          error.config.headers.Authorization = `Bearer ${data.access_token}`;
          return portalClient.request(error.config);
        } catch {
          localStorage.removeItem("portal_token");
          localStorage.removeItem("portal_refresh");
          localStorage.removeItem("portal_user");
          window.location.href = "/portal/login";
        }
      } else {
        window.location.href = "/portal/login";
      }
    }
    return Promise.reject(error);
  }
);

export default portalClient;
