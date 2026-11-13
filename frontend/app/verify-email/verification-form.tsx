"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import axios from "axios";
import {
  ArrowLeft,
  CheckCircle2,
  Code2,
  LoaderCircle,
  MailCheck,
  ShieldAlert,
} from "lucide-react";

import { useAuth } from "../../components/providers/auth-provider";

type VerificationStatus =
  | "idle"
  | "verifying"
  | "success"
  | "error";

interface VerificationFormProps {
  token: string | null;
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    const message = error.response?.data?.message;

    if (typeof detail === "string") {
      return detail;
    }

    if (typeof message === "string") {
      return message;
    }

    if (!error.response) {
      return "Unable to reach the server. Check your connection and try again.";
    }
  }

  return "We could not verify your email address. Please try again.";
}

export default function VerificationForm({
  token,
}: VerificationFormProps) {
  const router = useRouter();
  const { verifyEmailAddress } = useAuth();

  const [status, setStatus] = useState<VerificationStatus>(
    token ? "idle" : "error",
  );
  const [errorMessage, setErrorMessage] = useState(
    token ? "" : "The verification link is missing its token.",
  );

  async function handleVerification() {
    if (!token || status === "verifying" || status === "success") {
      return;
    }

    setStatus("verifying");
    setErrorMessage("");

    // Remove the sensitive token from the visible browser URL.
    router.replace("/verify-email", { scroll: false });

    try {
      await verifyEmailAddress({ token });
      setStatus("success");
    } catch (error: unknown) {
      setErrorMessage(getErrorMessage(error));
      setStatus("error");
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#080d18] px-6 py-12 text-slate-100">
      <div className="w-full max-w-md">
        <Link
          href="/"
          className="mb-10 inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"
        >
          <ArrowLeft size={16} />
          Back to home
        </Link>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-8 shadow-2xl shadow-black/20">
          <Link href="/" className="mb-10 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500 text-white">
              <Code2 size={23} />
            </div>

            <span className="text-xl font-semibold tracking-tight">
              SherlskyyCommand
            </span>
          </Link>

          {status === "success" ? (
            <div>
              <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/10">
                <CheckCircle2 size={32} className="text-emerald-400" />
              </div>

              <h1 className="text-3xl font-bold tracking-tight">
                Email verified!
              </h1>

              <p className="mt-4 leading-7 text-slate-400">
                Your email address has been successfully verified.
                You can now sign in to your SherlskyyCommand account.
              </p>

              <Link
                href="/login"
                className="mt-8 flex w-full items-center justify-center rounded-xl bg-blue-600 px-5 py-3.5 font-semibold text-white transition hover:bg-blue-500"
              >
                Continue to sign in
              </Link>
            </div>
          ) : status === "error" ? (
            <div>
              <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-red-500/10">
                <ShieldAlert size={32} className="text-red-400" />
              </div>

              <h1 className="text-3xl font-bold tracking-tight">
                Verification unsuccessful
              </h1>

              <p
                role="alert"
                className="mt-4 leading-7 text-slate-400"
              >
                {errorMessage}
              </p>

              <p className="mt-4 text-sm leading-6 text-slate-500">
                Verification links expire after 30 minutes and can only
                be used once. You may need a new verification email.
              </p>

              <Link
                href="/login"
                className="mt-8 flex w-full items-center justify-center rounded-xl border border-white/10 bg-white/[0.05] px-5 py-3.5 font-semibold text-white transition hover:bg-white/10"
              >
                Go to sign in
              </Link>
            </div>
          ) : (
            <div>
              <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-blue-500/10">
                {status === "verifying" ? (
                  <LoaderCircle
                    size={32}
                    className="animate-spin text-blue-400"
                  />
                ) : (
                  <MailCheck size={32} className="text-blue-400" />
                )}
              </div>

              <h1 className="text-3xl font-bold tracking-tight">
                Verify your email
              </h1>

              <p className="mt-4 leading-7 text-slate-400">
                Confirm that you own this email address to activate
                your SherlskyyCommand account.
              </p>

              <button
                type="button"
                onClick={handleVerification}
                disabled={status === "verifying"}
                className="mt-8 flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3.5 font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {status === "verifying" ? (
                  <>
                    <LoaderCircle size={18} className="animate-spin" />
                    Verifying email...
                  </>
                ) : (
                  "Verify email address"
                )}
              </button>
            </div>
          )}
        </div>

        <p className="mt-8 text-center text-xs text-slate-600">
          SherlskyyCommand · Secure account verification
        </p>
      </div>
    </main>
  );
}
