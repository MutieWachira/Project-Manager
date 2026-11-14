import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { AppState } from 'react-native';

import { ApiError } from '@/lib/api/api-errors';

import {
  getCurrentUser,
  loginUser,
  logoutUser,
  refreshSession,
  registerUser,
  verifyEmail,
  verifyMFA,
} from '@/lib/auth/auth-service';

import {
  deleteRefreshToken,
  getRefreshToken,
} from '@/lib/auth/token-storage';

import type {
  AuthenticatedLoginResponse,
  CurrentUser,
  LoginResponse,
  RegisterRequest,
  VerifyEmailRequest,
} from '@/lib/auth/auth-types';

// ---------------------------------------------------------
// Authentication state
// ---------------------------------------------------------

export type AuthStatus =
  | 'loading'
  | 'authenticated'
  | 'unauthenticated'
  | 'mfa_required';

export type LoginResult =
  | {
      mfaRequired: true;
      challengeExpiresAt: string;
    }
  | {
      mfaRequired: false;
    };

interface AuthContextValue {
  status: AuthStatus;
  user: CurrentUser | null;
  accessToken: string | null;
  authError: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  register: (payload: RegisterRequest) => Promise<void>;
  verifyEmailAddress: (payload: VerifyEmailRequest) => Promise<void>;
  login: (
    email: string,
    password: string,
    deviceName?: string,
  ) => Promise<LoginResult>;
  completeMFA: (code: string, deviceName?: string) => Promise<void>;
  cancelMFA: () => void;
  retrySessionRestore: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ---------------------------------------------------------
// Prevent concurrent refresh-token rotations.
// ---------------------------------------------------------

let refreshPromise: ReturnType<typeof refreshSession> | null = null;

function getSharedRefreshSession() {
  if (!refreshPromise) {
    refreshPromise = refreshSession().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

// ---------------------------------------------------------
// Authentication provider
// ---------------------------------------------------------

export function AuthProvider({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [accessTokenExpiresAt, setAccessTokenExpiresAt] =
    useState<number | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);

  const [pendingMFA, setPendingMFA] = useState<{
    challengeToken: string;
    expiresAt: string;
  } | null>(null);

  // -------------------------------------------------------
  // Clear the in-memory authentication state.
  // -------------------------------------------------------

  const clearSessionState = useCallback(() => {
    setAccessToken(null);
    setAccessTokenExpiresAt(null);
    setUser(null);
    setPendingMFA(null);
    setStatus('unauthenticated');
  }, []);

  // -------------------------------------------------------
  // Restore an existing session.
  // -------------------------------------------------------

  const restoreSession = useCallback(async (isCancelled: () => boolean = () => false) => {
    setAuthError(null);
    setPendingMFA(null);

    try {
      const savedToken = await getRefreshToken();

      if (isCancelled()) return;

      if (!savedToken) {
        clearSessionState();
        return;
      }

      const session = await getSharedRefreshSession();

      if (isCancelled()) return;

      const currentUser = await getCurrentUser(session.access_token);

      if (isCancelled()) return;

      setAccessToken(session.access_token);
      setAccessTokenExpiresAt(
        Date.now() + session.expires_in * 1000,
      );
      setUser(currentUser);
      setPendingMFA(null);
      setStatus('authenticated');
    } catch (error) {
      if (isCancelled()) return;

      if (error instanceof ApiError && error.status === 401) {
        try {
          await deleteRefreshToken();
        } catch {
          // Clear in-memory state even if secure storage fails.
        }
      }

      clearSessionState();

      if (!(error instanceof ApiError && error.status === 401)) {
        setAuthError(
          error instanceof Error
            ? error.message
            : 'Unable to restore your session.',
        );
      }
    }
  }, [clearSessionState]);

  // -------------------------------------------------------
  // Restore a saved session when the app starts.
  // -------------------------------------------------------

  useEffect(() => {
    let cancelled = false;

    async function initializeAuthentication() {
      await restoreSession(() => cancelled);

      if (cancelled) {
        return;
      }
    }

    void initializeAuthentication();

    return () => {
      cancelled = true;
    };
  }, [restoreSession]);

  // -------------------------------------------------------
  // Refresh the access token before it expires.
  // -------------------------------------------------------

  useEffect(() => {
    if (
      status !== 'authenticated' ||
      !accessToken ||
      accessTokenExpiresAt === null
    ) {
      return;
    }

    let cancelled = false;
    let refreshInProgress = false;
    let refreshTimeout: ReturnType<typeof setTimeout> | undefined;
    let retryTimeout: ReturnType<typeof setTimeout> | undefined;

    const refreshBeforeExpiryMs = Math.min(
      60_000,
      Math.max(5_000, (accessTokenExpiresAt - Date.now()) * 0.1),
    );

    const refreshDelay = Math.max(
      0,
      accessTokenExpiresAt - Date.now() - refreshBeforeExpiryMs,
    );

    async function refreshAccessToken() {
      if (refreshInProgress || cancelled) {
        return;
      }

      refreshInProgress = true;

      try {
        const session = await getSharedRefreshSession();

        if (cancelled) {
          return;
        }

        setAccessToken(session.access_token);
        setAccessTokenExpiresAt(
          Date.now() + session.expires_in * 1000,
        );
        setAuthError(null);
      } catch (error) {
        if (cancelled) {
          return;
        }

        if (error instanceof ApiError && error.status === 401) {
          try {
            await deleteRefreshToken();
          } catch {
            // The in-memory session must still be cleared.
          }

          clearSessionState();
          setAuthError('Your session has expired. Please sign in again.');
          return;
        }

        setAuthError(
          'Unable to refresh your session. Retrying automatically.',
        );

        retryTimeout = setTimeout(() => {
          void refreshAccessToken();
        }, 15_000);
      } finally {
        refreshInProgress = false;
      }
    }

    refreshTimeout = setTimeout(() => {
      void refreshAccessToken();
    }, refreshDelay);

    const subscription = AppState.addEventListener(
      'change',
      (nextAppState) => {
        if (
          nextAppState === 'active' &&
          Date.now() >= accessTokenExpiresAt - refreshBeforeExpiryMs
        ) {
          void refreshAccessToken();
        }
      },
    );

    return () => {
      cancelled = true;

      if (refreshTimeout) {
        clearTimeout(refreshTimeout);
      }

      if (retryTimeout) {
        clearTimeout(retryTimeout);
      }

      subscription.remove();
    };
  }, [
    accessToken,
    accessTokenExpiresAt,
    status,
    clearSessionState,
  ]);

  // -------------------------------------------------------
  // Registration.
  // -------------------------------------------------------

  const register = useCallback(async (payload: RegisterRequest) => {
    await registerUser(payload);
  }, []);

  // -------------------------------------------------------
  // Email verification.
  // -------------------------------------------------------

  const verifyEmailAddress = useCallback(
    async (payload: VerifyEmailRequest) => {
      await verifyEmail(payload);
    },
    [],
  );

  // -------------------------------------------------------
  // Establish an authenticated session.
  // -------------------------------------------------------

  const establishAuthenticatedSession = useCallback(
    async (response: AuthenticatedLoginResponse) => {
      try {
        const currentUser = await getCurrentUser(response.access_token);

        setAccessToken(response.access_token);
        setAccessTokenExpiresAt(
          Date.now() + response.expires_in * 1000,
        );
        setUser(currentUser);
        setPendingMFA(null);
        setAuthError(null);
        setStatus('authenticated');
      } catch (error) {
        clearSessionState();
        throw error;
      }
    },
    [clearSessionState],
  );

  // -------------------------------------------------------
  // Login.
  // -------------------------------------------------------

  const login = useCallback(
    async (
      email: string,
      password: string,
      deviceName?: string,
    ): Promise<LoginResult> => {
      setAuthError(null);

      const response: LoginResponse = await loginUser({
        email,
        password,
        device_name: deviceName,
      });

      if (response.mfa_required) {
        setAccessToken(null);
        setAccessTokenExpiresAt(null);
        setUser(null);

        setPendingMFA({
          challengeToken: response.challenge_token,
          expiresAt: response.challenge_expires_at,
        });

        setStatus('mfa_required');

        return {
          mfaRequired: true,
          challengeExpiresAt: response.challenge_expires_at,
        };
      }

      await establishAuthenticatedSession(response);

      return {
        mfaRequired: false,
      };
    },
    [establishAuthenticatedSession],
  );

    // -------------------------------------------------------
  // Complete MFA verification.
  // -------------------------------------------------------

  const completeMFA = useCallback(
    async (code: string, deviceName?: string) => {
      if (!pendingMFA) {
        throw new Error('No active MFA challenge was found.');
      }

      const expiresAt = Date.parse(pendingMFA.expiresAt);

      if (!Number.isFinite(expiresAt) || expiresAt <= Date.now()) {
        setPendingMFA(null);
        setAuthError(null);
        setStatus('unauthenticated');

        throw new Error(
          'Your verification challenge has expired. Please sign in again.',
        );
      }

      setAuthError(null);

      const response = await verifyMFA({
        challenge_token: pendingMFA.challengeToken,
        code,
        device_name: deviceName,
      });

      await establishAuthenticatedSession(response);
    },
    [pendingMFA, establishAuthenticatedSession],
  );

  // -------------------------------------------------------
  // Cancel an outstanding MFA challenge.
  // -------------------------------------------------------

  const cancelMFA = useCallback(() => {
    setPendingMFA(null);
    setAuthError(null);
    setStatus('unauthenticated');
  }, []);

  // -------------------------------------------------------
  // Retry session restoration after a network failure.
  // -------------------------------------------------------

  const retrySessionRestore = useCallback(async () => {
    setStatus('loading');
    await restoreSession();
  }, [restoreSession]);

  // -------------------------------------------------------
  // Logout.
  // -------------------------------------------------------

  const logout = useCallback(async () => {
    setAuthError(null);

    try {
      await logoutUser();
    } finally {
      clearSessionState();
    }
  }, [clearSessionState]);

  // -------------------------------------------------------
  // Context value.
  // -------------------------------------------------------

  const value: AuthContextValue = {
    status,
    user,
    accessToken,
    authError,
    isLoading: status === 'loading',
    isAuthenticated: status === 'authenticated',

    register,
    verifyEmailAddress,
        login,
    completeMFA,
    cancelMFA,
    retrySessionRestore,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// ---------------------------------------------------------
// Authentication hook.
// ---------------------------------------------------------

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used inside an AuthProvider.');
  }

  return context;
}
