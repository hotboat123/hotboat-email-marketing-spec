import axios from "axios";

// Use NEXT_PUBLIC_API_URL (set in Railway frontend service Variables at build time).
// Falls back to relative /api for local dev (proxied via next.config.mjs rewrite).
const BASE = process.env.NEXT_PUBLIC_API_URL || "";
export const api = axios.create({ baseURL: `${BASE}/api` });

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("hb_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("hb_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// Auth
export const authApi = {
  login: (email: string, password: string) => {
    const form = new URLSearchParams({ username: email, password });
    return api.post<{ access_token: string }>("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },
  me: () => api.get("/auth/me"),
};

// Contacts
export const contactsApi = {
  list: (params?: { skip?: number; limit?: number; search?: string; opted_in?: boolean }) =>
    api.get("/contacts/", { params }),
  get: (id: number) => api.get(`/contacts/${id}`),
  create: (data: unknown) => api.post("/contacts/", data),
  update: (id: number, data: unknown) => api.patch(`/contacts/${id}`, data),
  delete: (id: number) => api.delete(`/contacts/${id}`),
  importCsv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/contacts/import/csv", form);
  },
};

// Segments
export const segmentsApi = {
  list: () => api.get("/segments/"),
  get: (id: number) => api.get(`/segments/${id}`),
  create: (data: unknown) => api.post("/segments/", data),
  update: (id: number, data: unknown) => api.patch(`/segments/${id}`, data),
  delete: (id: number) => api.delete(`/segments/${id}`),
  preview: (id: number) => api.get(`/segments/${id}/preview`),
};

// Templates
export const templatesApi = {
  list: () => api.get("/templates/"),
  get: (id: number) => api.get(`/templates/${id}`),
  create: (data: unknown) => api.post("/templates/", data),
  update: (id: number, data: unknown) => api.patch(`/templates/${id}`, data),
  delete: (id: number) => api.delete(`/templates/${id}`),
  duplicate: (id: number) => api.post(`/templates/${id}/duplicate`),
};

// Campaigns
export const campaignsApi = {
  list: () => api.get("/campaigns/"),
  get: (id: number) => api.get(`/campaigns/${id}`),
  create: (data: unknown) => api.post("/campaigns/", data),
  update: (id: number, data: unknown) => api.patch(`/campaigns/${id}`, data),
  delete: (id: number) => api.delete(`/campaigns/${id}`),
  send: (id: number) => api.post(`/campaigns/${id}/send`),
  sendTest: (id: number) => api.post(`/campaigns/${id}/send-test`),
  stats: (id: number) => api.get(`/campaigns/${id}/stats`),
};

// Analytics
export const analyticsApi = {
  overview: () => api.get("/analytics/overview"),
  recentCampaigns: () => api.get("/analytics/campaigns/recent"),
};

// Sync
export const syncApi = {
  run: () => api.post("/sync/run"),
  status: () => api.get("/sync/status"),
};
