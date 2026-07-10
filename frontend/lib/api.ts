import axios from "axios";

// Always use relative /api — the Next.js proxy route at app/api/[...path]/route.ts
// forwards to BACKEND_URL at runtime. No build-time env vars needed in the browser.
export const api = axios.create({ baseURL: "/api" });

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
    // Only force-logout if the token itself is rejected, not on any random 401.
    // Avoids logout loops caused by cold-start errors or momentary backend failures.
    if (err.response?.status === 401 && typeof window !== "undefined") {
      const url: string = err.config?.url ?? "";
      const isAuthCheck = url.includes("/auth/");
      if (isAuthCheck) {
        localStorage.removeItem("hb_token");
        window.location.href = "/login";
      }
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
    api.get("/contacts", { params }),
  get: (id: number) => api.get(`/contacts/${id}`),
  create: (data: unknown) => api.post("/contacts", data),
  update: (id: number, data: unknown) => api.patch(`/contacts/${id}`, data),
  delete: (id: number) => api.delete(`/contacts/${id}`),
  segments: (id: number) => api.get(`/contacts/${id}/segments`),
  bookings: (id: number) => api.get(`/contacts/${id}/bookings`),
  emailActivity: (id: number) => api.get(`/contacts/${id}/email_activity`),
  emailSends: (id: number) => api.get(`/contacts/${id}/email_sends`),
  importCsv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/contacts/import/csv", form);
  },
};

// Segments
export const segmentsApi = {
  list: () => api.get("/segments"),
  get: (id: number) => api.get(`/segments/${id}`),
  create: (data: unknown) => api.post("/segments", data),
  update: (id: number, data: unknown) => api.patch(`/segments/${id}`, data),
  delete: (id: number) => api.delete(`/segments/${id}`),
  preview: (id: number) => api.get(`/segments/${id}/preview`),
};

// Templates
export const templatesApi = {
  list: () => api.get("/templates"),
  get: (id: number) => api.get(`/templates/${id}`),
  create: (data: unknown) => api.post("/templates", data),
  update: (id: number, data: unknown) => api.patch(`/templates/${id}`, data),
  delete: (id: number) => api.delete(`/templates/${id}`),
  duplicate: (id: number) => api.post(`/templates/${id}/duplicate`),
};

// Campaigns
export const campaignsApi = {
  list: () => api.get("/campaigns"),
  get: (id: number) => api.get(`/campaigns/${id}`),
  create: (data: unknown) => api.post("/campaigns", data),
  update: (id: number, data: unknown) => api.patch(`/campaigns/${id}`, data),
  delete: (id: number) => api.delete(`/campaigns/${id}`),
  send: (id: number, limit?: number) => api.post(`/campaigns/${id}/send`, limit ? { limit } : {}),
  sendTest: (id: number) => api.post(`/campaigns/${id}/send-test`),
  sendProgress: (id: number) => api.get(`/campaigns/${id}/send-progress`),
  stats: (id: number) => api.get(`/campaigns/${id}/stats`),
  conversions: (id: number, days = 60) => api.get(`/campaigns/${id}/conversions?days=${days}`),
  sends: (id: number) => api.get(`/campaigns/${id}/sends`),
};

// Marca
export const marcaApi = {
  list: (categoria?: string) => api.get("/marca", { params: categoria ? { categoria } : {} }),
  create: (data: { categoria: string; nombre: string; valor: string; descripcion?: string }) =>
    api.post("/marca", data),
  update: (id: number, data: Partial<{ categoria: string; nombre: string; valor: string; descripcion: string }>) =>
    api.put(`/marca/${id}`, data),
  remove: (id: number) => api.delete(`/marca/${id}`),
};

// Analytics
export const analyticsApi = {
  overview: () => api.get("/analytics/overview"),
  recentCampaigns: () => api.get("/analytics/campaigns/recent"),
  asuntos: () => api.get("/analytics/asuntos"),
};

// Signup Forms
export const formsApi = {
  list: () => api.get("/forms"),
  get: (id: number) => api.get(`/forms/${id}`),
  create: (data: unknown) => api.post("/forms", data),
  update: (id: number, data: unknown) => api.patch(`/forms/${id}`, data),
  delete: (id: number) => api.delete(`/forms/${id}`),
  submissions: (id: number) => api.get(`/forms/${id}/submissions`),
};

// Automations
export const automationsApi = {
  list: () => api.get("/automations"),
  get: (id: number) => api.get(`/automations/${id}`),
  create: (data: unknown) => api.post("/automations", data),
  update: (id: number, data: unknown) => api.patch(`/automations/${id}`, data),
  delete: (id: number) => api.delete(`/automations/${id}`),
  toggle: (id: number) => api.post(`/automations/${id}/toggle`),
  test: (id: number) => api.post(`/automations/${id}/test`),
  runs: (id: number) => api.get(`/automations/${id}/runs`),
  stats: (id: number) => api.get(`/automations/${id}/stats`),
};

// CRM (cola de llamadas)
export const crmApi = {
  list: (params?: { call_status?: string; min_score?: number; ad_source?: string; skip?: number; limit?: number }) =>
    api.get("/crm/contacts", { params }),
  get: (id: number) => api.get(`/crm/contacts/${id}`),
  getByContact: (contactId: number) => api.get(`/crm/contacts/by_contact/${contactId}`),
  callActivity: (id: number) => api.get(`/crm/contacts/${id}/call_activity`),
  conversations: (id: number) => api.get(`/crm/contacts/${id}/conversations`),
  webActivity: (id: number) => api.get(`/crm/contacts/${id}/web_activity`),
  updateCallStatus: (id: number, data: { call_status: string; note?: string }) =>
    api.patch(`/crm/contacts/${id}/call_status`, data),
  // Bearer token vive en localStorage, no en cookies, asi que la descarga no puede ser un <a href> plano:
  // pedimos el CSV como blob (con el interceptor de auth) y disparamos la descarga en el cliente.
  exportCsv: async (params?: { call_status?: string; min_score?: number }) => {
    const res = await api.get("/crm/contacts/export/csv", { params, responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const a = document.createElement("a");
    a.href = url;
    a.download = "crm_contacts.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },
};

// Sync
export const syncApi = {
  run: () => api.post("/sync/run"),
  status: () => api.get("/sync/status"),
  importTc: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/sync/tc-import", form);
  },
};
