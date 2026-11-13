import { API_BASE_URL, ApiError, readErrorDetail, setToken, removeToken } from "./client";

export interface AuthUser {
  user_id: string;
  full_name: string;
  email: string;
  access_token: string;
  role?: "admin" | "user";
}

export interface RegisterParams {
  full_name: string;
  email: string;
  password: string;
}

export interface LoginParams {
  email: string;
  password: string;
}

/** Register a new user and return the token response. */
export async function register(params: RegisterParams): Promise<AuthUser> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  const data = (await response.json()) as AuthUser;
  setToken(data.access_token);
  return data;
}

/** Log in an existing user and return the token response. */
export async function login(params: LoginParams): Promise<AuthUser> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  const data = (await response.json()) as AuthUser;
  setToken(data.access_token);
  return data;
}

/** Clear the stored token (client-side logout). */
export function logout(): void {
  removeToken();
}
