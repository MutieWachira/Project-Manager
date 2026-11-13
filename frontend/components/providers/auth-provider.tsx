"use client";

import axios from "axios";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  getCurrentUser,
  loginUser,
  logoutUser,
  refreshSession,
  registerUser,
  verifyEmail,
  verifyMFA,
} from "../../lib/auth-service";

import type {
  AuthenticatedLoginResponse,
  CurrentUser,
  LoginRequest,
  RegisterRequest,
  VerifyEmailRequest,
} from "../../lib/auth-service";

// ---------------------------------------------------------
// Authentication state
// ---------------------------------------------------------

export type AuthStatus =
  | "loading"
  | "authenticated"
  | "unauthenticated"
  | "mfa_required";

export type LoginResult =
  | {
      mfaRequired: true;
      challengeExpiresAt: string;
    }
  | {
      mfaRequired: false;
    };

type WebLoginInput = Omit<LoginRequest, "client_type">;

interface AuthContextValue {
  status: AuthStatus;
  user: CurrentUser | null;
  accessToken: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  register: (payload: RegisterRequest) => Promise<void>;
  verifyEmailAddress: (payload: VerifyEmailRequest) => Promise<void>;
  login: (payload: WebLoginInput) => Promise<LoginResult>;
  completeMFA: (code: string, deviceName?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ---------------------------------------------------------
// Prevent simultaneous refresh-token rotations.
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
  children: React.ReactNode;
}>) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [accessTokenExpiresAt, setAccessTokenExpiresAt] = useState<number | null>(
    null,
  );

  const [pendingMFA, setPendingMFA] = useState<{
    challengeToken: string;
    expiresAt: string;
  } | null>(null);

  // -------------------------------------------------------
  // Restore an existing session when the application loads.
  // -------------------------------------------------------

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      try {
        const session = await getSharedRefreshSession();

        const currentUser = await getCurrentUser(session.access_token);

        if (cancelled) {
          return;
        }

        setAccessToken(session.access_token);
        setAccessTokenExpiresAt(Date.now() + session.expires_in * 1000);
        setUser(currentUser);
        setStatus("authenticated");
      } catch {
        if (cancelled) {
          return;
        }

        setAccessToken(null);
        setAccessTokenExpiresAt(null);
        setUser(null);
        setPendingMFA(null);
        setStatus("unauthenticated");
      }
    }

    void restoreSession().finally(() => {
      if (!cancelled) {
        setStatus((currentStatus) =>
          currentStatus === "loading" ? "unauthenticated" : currentStatus,
        );
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  // -------------------------------------------------------
  // Refresh the access token before it expires.
  // -------------------------------------------------------

  useEffect(() => {
    if (
      status !== "authenticated" ||
      !accessToken ||
      accessTokenExpiresAt === null
    ) {
      return;
    }

    const tokenExpiresAt = accessTokenExpiresAt;
    let cancelled = false;
    let refreshInProgress = false;
    let retryTimeout: ReturnType<typeof setTimeout> | undefined;

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
        setAccessTokenExpiresAt(Date.now() + session.expires_in * 1000);
      } catch (error: unknown) {
        if (cancelled) {
          return;
        }

        if (axios.isAxiosError(error) && error.response?.status === 401) {
          setAccessToken(null);
          setAccessTokenExpiresAt(null);
          setUser(null);
          setPendingMFA(null);
          setStatus("unauthenticated");
          return;
        }

        retryTimeout = setTimeout(() => {
          void refreshAccessToken();
        }, 15_000);
      } finally {
        refreshInProgress = false;
      }
    }

    const refreshBeforeExpiryMs = Math.min(
      60_000,
      Math.max(30_000, (tokenExpiresAt - Date.now()) * 0.1),
    );
    const refreshDelay = Math.max(
      0,
      tokenExpiresAt - Date.now() - refreshBeforeExpiryMs,
    );
    const refreshTimeout = setTimeout(() => {
      void refreshAccessToken();
    }, refreshDelay);

    function handleVisibilityChange() {
      if (
        document.visibilityState === "visible" &&
        Date.now() >= tokenExpiresAt - refreshBeforeExpiryMs
      ) {
        void refreshAccessToken();
      }
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      cancelled = true;
      clearTimeout(refreshTimeout);
      if (retryTimeout !== undefined) {
        clearTimeout(retryTimeout);
      }
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [accessToken, accessTokenExpiresAt, status]);

  // -------------------------------------------------------
  // Registration
  // -------------------------------------------------------

  const register = useCallback(async (payload: RegisterRequest) => {
    await registerUser(payload);
  }, []);

  // -------------------------------------------------------
  // Email verification
  // -------------------------------------------------------

  const verifyEmailAddress = useCallback(
    async (payload: VerifyEmailRequest) => {
      await verifyEmail(payload);
    },
    [],
  );

  // -------------------------------------------------------
  // Login
  // -------------------------------------------------------

  const login = useCallback(
    async (payload: WebLoginInput): Promise<LoginResult> => {
      const response = await loginUser({
        ...payload,
        client_type: "web",
      });

      if (response.mfa_required) {
        setAccessToken(null);
        setAccessTokenExpiresAt(null);
        setUser(null);

        setPendingMFA({
          challengeToken: response.challenge_token,
          expiresAt: response.challenge_expires_at,
        });

        setStatus("mfa_required");

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
    [],
  );

  // -------------------------------------------------------
  // Establish a completed authenticated session.
  // -------------------------------------------------------

  async function establishAuthenticatedSession(
    response: AuthenticatedLoginResponse,
  ) {
    try {
      const currentUser = await getCurrentUser(response.access_token);

      setAccessToken(response.access_token);
      setAccessTokenExpiresAt(Date.now() + response.expires_in * 1000);
      setUser(currentUser);
      setPendingMFA(null);
      setStatus("authenticated");
    } catch (error) {
      setAccessToken(null);
      setAccessTokenExpiresAt(null);
      setUser(null);
      setPendingMFA(null);
      setStatus("unauthenticated");

      throw error;
    }
  }

  // -------------------------------------------------------
  // Complete MFA verification.
  // -------------------------------------------------------

  const completeMFA = useCallback(
    async (code: string, deviceName?: string) => {
      if (!pendingMFA) {
        throw new Error("No active MFA challenge was found.");
      }

      const response = await verifyMFA({
        challenge_token: pendingMFA.challengeToken,
        code,
        device_name: deviceName,
      });

      await establishAuthenticatedSession(response);
    },
    [pendingMFA],
  );

  // -------------------------------------------------------
  // Logout
  // -------------------------------------------------------

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } finally {
      setAccessToken(null);
      setAccessTokenExpiresAt(null);
      setUser(null);
      setPendingMFA(null);
      setStatus("unauthenticated");
    }
  }, []);

  // -------------------------------------------------------
  // Context value
  // -------------------------------------------------------

  const value: AuthContextValue = {
    status,
    user,
    accessToken,
    isLoading: status === "loading",
    isAuthenticated: status === "authenticated",

    register,
    verifyEmailAddress,
    login,
    completeMFA,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// ---------------------------------------------------------
// Authentication hook
// ---------------------------------------------------------

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside an AuthProvider.");
  }

  return context;
}
