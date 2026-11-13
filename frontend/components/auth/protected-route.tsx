
"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { LoaderCircle, ShieldAlert } from "lucide-react";

import { useAuth } from "../providers/auth-provider";

interface ProtectedRouteProps {
  children: ReactNode;
}

/**
 * Protects application routes from unauthenticated access.
 *
 * Authentication is checked using the shared AuthProvider.
 * The component waits for session restoration before redirecting.
 */
export default function ProtectedRoute({
  children,
}: ProtectedRouteProps) {
  const router = useRouter();
  const { status } = useAuth();

  useEffect(() => {
    if (
      status === "unauthenticated" ||
      status === "mfa_required"
    ) {
      router.replace("/login");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <div className="flex flex-col items-center gap-4">
          <LoaderCircle
            size={36}
            className="animate-spin text-blue-500"
          />

          <p className="text-sm text-slate-400">
            Restoring your session...
          </p>
        </div>
      </main>
    );
  }

  if (status === "unauthenticated" || status === "mfa_required") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-white">
        <div className="flex max-w-md flex-col items-center text-center">
          <ShieldAlert size={36} className="text-blue-400" />

          <h1 className="mt-5 text-xl font-semibold">
            Authentication required
          </h1>

          <p className="mt-3 text-sm leading-6 text-slate-400">
            Redirecting you to the sign-in page...
          </p>
        </div>
      </main>
    );
  }

  return <>{children}</>;
}
