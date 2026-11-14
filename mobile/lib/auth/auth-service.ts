import { apiRequest } from '@/lib/api/api-client';

import {
  deleteRefreshToken,
  getRefreshToken,
  saveRefreshToken,
} from './token-storage';

import type {
  ApiMessageResponse,
  AuthenticatedLoginResponse,
  CurrentUser,
  LoginRequest,
  LoginResponse,
  MobileRefreshResponse,
  RefreshResponse,
  RegisterRequest,
  VerifyEmailRequest,
  VerifyMFARequest,
} from './auth-types';

/**
 * Ensures that a completed mobile login contains all required
 * session fields before the refresh token is persisted.
 */
async function persistLoginSession(
  response: LoginResponse,
): Promise<LoginResponse> {
  if (response.mfa_required) {
    return response;
  }

  if (
    !response.access_token ||
    !response.refresh_token ||
    !response.session_id ||
    typeof response.expires_in !== 'number'
  ) {
    throw new Error(
      'The server returned an incomplete authentication response.',
    );
  }

  await saveRefreshToken(response.refresh_token);

  return response;
}

/**
 * Register a new user account.
 */
export async function registerUser(
  request: RegisterRequest,
): Promise<ApiMessageResponse> {
  return apiRequest<ApiMessageResponse>('/auth/register', {
    method: 'POST',
    body: request,
  });
}

/**
 * Verify a user's email address.
 */
export async function verifyEmail(
  request: VerifyEmailRequest,
): Promise<ApiMessageResponse> {
  return apiRequest<ApiMessageResponse>('/auth/verify-email', {
    method: 'POST',
    body: request,
  });
}

/**
 * Authenticate a mobile user.
 *
 * The backend either returns an MFA challenge or a completed
 * session. Only completed sessions are saved to SecureStore.
 */
export async function loginUser(
  request: Omit<LoginRequest, 'client_type'>,
): Promise<LoginResponse> {
  const response = await apiRequest<LoginResponse>('/auth/login', {
    method: 'POST',
    body: {
      ...request,
      client_type: 'mobile',
    },
  });

  return persistLoginSession(response);
}

/**
 * Complete an MFA login challenge.
 */
export async function verifyMFA(
  request: VerifyMFARequest,
): Promise<AuthenticatedLoginResponse> {
  const response = await apiRequest<LoginResponse>('/auth/mfa/verify', {
    method: 'POST',
    body: request,
  });

  if (response.mfa_required) {
    throw new Error(
      'The server did not complete the MFA authentication challenge.',
    );
  }

  const authenticatedResponse = await persistLoginSession(response);

  if (authenticatedResponse.mfa_required) {
    throw new Error('MFA authentication was not completed.');
  }

  return authenticatedResponse;
}

/**
 * Rotate the mobile refresh token.
 *
 * The replacement token must be saved before this function
 * returns the new access token to the authentication provider.
 */
export async function refreshSession(): Promise<MobileRefreshResponse> {
  const refreshToken = await getRefreshToken();

  if (!refreshToken) {
    throw new Error('No saved refresh token is available.');
  }

  const response = await apiRequest<RefreshResponse>('/auth/refresh', {
    method: 'POST',
    body: {
      refresh_token: refreshToken,
    },
  });

  if (!response.access_token || !response.refresh_token) {
    throw new Error(
      'The server returned an incomplete refreshed session.',
    );
  }

  await saveRefreshToken(response.refresh_token);

  return response as MobileRefreshResponse;
}

/**
 * Retrieve the currently authenticated user's profile.
 */
export async function getCurrentUser(
  accessToken: string,
): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/auth/me', {
    method: 'GET',
    accessToken,
  });
}

/**
 * Revoke the current mobile session and clear local credentials.
 *
 * Local token deletion happens even if the server request fails.
 */
export async function logoutUser(): Promise<ApiMessageResponse | null> {
  try {
    const refreshToken = await getRefreshToken();

    if (!refreshToken) {
      return null;
    }

    return await apiRequest<ApiMessageResponse>('/auth/logout', {
      method: 'POST',
      body: {
        refresh_token: refreshToken,
      },
    });
  } finally {
    await deleteRefreshToken();
  }
}
