export interface ApiMessageResponse {
  message: string;
}

export interface RegisterRequest {
  full_name: string;
  email: string;
  password: string;
}

export interface VerifyEmailRequest {
  token: string;
}

export interface LoginRequest {
  email: string;
  password: string;
  client_type: 'mobile';
  device_name?: string;
}

export interface VerifyMFARequest {
  challenge_token: string;
  code: string;
  device_name?: string;
}

export interface MFARequiredLoginResponse {
  mfa_required: true;
  challenge_token: string;
  challenge_expires_at: string;
  access_token: null;
  refresh_token: null;
  expires_in: null;
  session_id: null;
  session_expires_at: null;
  token_type: string;
}

export interface AuthenticatedLoginResponse {
  mfa_required: false;
  challenge_token: null;
  challenge_expires_at: null;
  access_token: string;
  refresh_token: string;
  expires_in: number;
  session_id: string;
  session_expires_at: string;
  token_type: string;
}

export type LoginResponse =
  | MFARequiredLoginResponse
  | AuthenticatedLoginResponse;

export interface RefreshRequest {
  refresh_token: string;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token: string | null;
  token_type: string;
  expires_in: number;
  session_id: string;
  session_expires_at: string;
}

export interface MobileRefreshResponse
  extends Omit<RefreshResponse, 'refresh_token'> {
  refresh_token: string;
}

export interface CurrentUser {
  id: string;
  full_name: string;
  email: string;
  is_active: boolean;
  email_verified: boolean;
}
