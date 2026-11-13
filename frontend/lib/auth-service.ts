import { apiClient } from "./api-client";

// ---------------------------------------------------------
// Shared API response
// ---------------------------------------------------------

export interface ApiMessageResponse {
  message: string;
}

// ---------------------------------------------------------
// Registration
// ---------------------------------------------------------

export interface RegisterRequest {
  full_name: string;
  email: string;
  password: string;
}

export type RegisterResponse = ApiMessageResponse;

// ---------------------------------------------------------
// Email verification
// ---------------------------------------------------------

export interface VerifyEmailRequest {
  token: string;
}

export type VerifyEmailResponse = ApiMessageResponse;

// ---------------------------------------------------------
// Login
// ---------------------------------------------------------

export interface LoginRequest {
  email: string;
  password: string;
  client_type: "web";
  device_name?: string;
}

/**
 * Returned when the account requires multi-factor authentication.
 * No authenticated session exists yet.
 */
export interface MFARequiredLoginResponse {
  mfa_required: true;
  challenge_token: string;
  challenge_expires_at: string;

  access_token: null;
  refresh_token: null;
  token_type: string;
  expires_in: null;

  session_id: null;
  session_expires_at: null;
}

/**
 * Returned when authentication has been completed successfully.
 * The web refresh token remains in the HttpOnly cookie.
 */
export interface AuthenticatedLoginResponse {
  mfa_required: false;
  challenge_token: null;
  challenge_expires_at: null;

  access_token: string;
  refresh_token: null;
  token_type: string;
  expires_in: number;

  session_id: string;
  session_expires_at: string;
}

/**
 * TypeScript can narrow this union using mfa_required.
 */
export type LoginResponse =
  | MFARequiredLoginResponse
  | AuthenticatedLoginResponse;

// ---------------------------------------------------------
// Multi-factor authentication
// ---------------------------------------------------------

export interface VerifyMFARequest {
  challenge_token: string;
  code: string;
  device_name?: string;
}

// ---------------------------------------------------------
// Session refresh
// ---------------------------------------------------------

export interface RefreshResponse {
  access_token: string;
  refresh_token: string | null;
  token_type: string;
  expires_in: number;
  session_id: string;
  session_expires_at: string;
}

// ---------------------------------------------------------
// Logout
// ---------------------------------------------------------

export type LogoutResponse = ApiMessageResponse;

// ---------------------------------------------------------
// Current authenticated user
// ---------------------------------------------------------

export interface CurrentUser {
  id: string;
  full_name: string;
  email: string;
  is_active: boolean;
  email_verified: boolean;
}

// ---------------------------------------------------------
// Authentication API service
// ---------------------------------------------------------

/**
 * Register a new account.
 *
 * The backend sends an email verification message.
 */
export async function registerUser(
  payload: RegisterRequest,
): Promise<RegisterResponse> {
  const response = await apiClient.post<RegisterResponse>(
    "/auth/register",
    payload,
  );

  return response.data;
}

/**
 * Verify an account using the email verification token.
 */
export async function verifyEmail(
  payload: VerifyEmailRequest,
): Promise<VerifyEmailResponse> {
  const response = await apiClient.post<VerifyEmailResponse>(
    "/auth/verify-email",
    payload,
  );

  return response.data;
}

/**
 * Authenticate a web user using email and password.
 *
 * The backend may return an MFA challenge instead of a completed session.
 * For web sessions, the refresh token is set as an HttpOnly cookie.
 */
export async function loginUser(
  payload: LoginRequest,
): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>(
    "/auth/login",
    payload,
  );

  return response.data;
}

/**
 * Complete login after successful MFA verification.
 */
export async function verifyMFA(
  payload: VerifyMFARequest,
): Promise<AuthenticatedLoginResponse> {
  const response = await apiClient.post<AuthenticatedLoginResponse>(
    "/auth/mfa/verify",
    payload,
  );

  return response.data;
}

/**
 * Request a new access token using the browser's HttpOnly refresh cookie.
 *
 * Never read or manually send the refresh cookie from frontend JavaScript.
 */
export async function refreshSession(): Promise<RefreshResponse> {
  const response = await apiClient.post<RefreshResponse>("/auth/refresh");

  return response.data;
}

/**
 * Revoke the current web session using the HttpOnly refresh cookie.
 */
export async function logoutUser(): Promise<LogoutResponse> {
  const response = await apiClient.post<LogoutResponse>("/auth/logout");

  return response.data;
}

/**
 * Retrieve the authenticated user's public profile.
 *
 * The access token is supplied by the authentication state manager.
 */
export async function getCurrentUser(
  accessToken: string,
): Promise<CurrentUser> {
  const response = await apiClient.get<CurrentUser>("/auth/me", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  return response.data;
}
