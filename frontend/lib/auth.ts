"use client";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("hb_token");
}

export function setToken(token: string) {
  localStorage.setItem("hb_token", token);
}

export function clearToken() {
  localStorage.removeItem("hb_token");
}

export function isAuthenticated(): boolean {
  return !!getToken();
}
