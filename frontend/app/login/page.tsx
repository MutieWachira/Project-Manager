"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import axios from "axios";
import {
  ArrowLeft,
  Code2,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from "lucide-react";

import { useAuth } from "../../components/providers/auth-provider";

import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

// ---------------------------------------------------------
// Validation schemas
// ---------------------------------------------------------

const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  password: z
    .string()
    .min(1, "Password is required.")
    .max(128, "Password is too long."),
});

const mfaSchema = z.object({
  code: z
    .string()
    .trim()
    .min(1, "Enter your authentication or recovery code.")
    .max(32, "The code is too long."),
});

type LoginFormValues = z.infer<typeof loginSchema>;
type MFAFormValues = z.infer<typeof mfaSchema>;

// ---------------------------------------------------------
// API error handling
// ---------------------------------------------------------

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const responseData: unknown = error.response?.data;

    if (
      typeof responseData === "object" &&
      responseData !== null &&
      "detail" in responseData &&
      typeof responseData.detail === "string"
    ) {
      return responseData.detail;
    }

    if (
      typeof responseData === "object" &&
      responseData !== null &&
      "message" in responseData &&
      typeof responseData.message === "string"
    ) {
      return responseData.message;
    }

    if (error.code === "ECONNABORTED") {
      return "The request timed out. Please try again.";
    }

    if (!error.response) {
      return "Unable to reach the server. Check your connection and try again.";
    }
  }

  return "Something went wrong. Please try again.";
}

// ---------------------------------------------------------
// Login page
// ---------------------------------------------------------

export default function LoginPage() {
  const router = useRouter();
  const {
    login,
    completeMFA,
    isAuthenticated,
    isLoading,
  } = useAuth();

  const [step, setStep] = useState<"login" | "mfa">("login");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // A successful password login, MFA verification, or restored session all
  // transition the shared auth state to authenticated. Send each of those
  // cases to the protected dashboard instead of leaving the user on login.
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, isLoading, router]);

  // Login form
  const loginForm = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  // MFA form
  const mfaForm = useForm<MFAFormValues>({
    resolver: zodResolver(mfaSchema),
    defaultValues: {
      code: "",
    },
  });

  // -------------------------------------------------------
  // Submit login credentials
  // -------------------------------------------------------

  async function handleLogin(values: LoginFormValues) {
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const result = await login({
        email: values.email,
        password: values.password,
      });

      if (result.mfaRequired) {
        setStep("mfa");
      }
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  // -------------------------------------------------------
  // Submit MFA verification
  // -------------------------------------------------------

  async function handleMFA(values: MFAFormValues) {
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await completeMFA(values.code);
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
      mfaForm.setValue("code", "");
    } finally {
      setIsSubmitting(false);
    }
  }

  // -------------------------------------------------------
  // Loading state
  // -------------------------------------------------------

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <div className="flex flex-col items-center gap-4">
          <LoaderCircle className="animate-spin text-blue-500" size={36} />
          <p className="text-sm text-slate-400">
            Checking your session...
          </p>
        </div>
      </main>
    );
  }

  // -------------------------------------------------------
  // Already authenticated
  // -------------------------------------------------------

  if (isAuthenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <div className="flex flex-col items-center gap-4">
          <LoaderCircle className="animate-spin text-blue-500" size={36} />
          <p className="text-sm text-slate-400">
            Opening your dashboard...
          </p>
        </div>
      </main>
    );
  }

  // -------------------------------------------------------
  // Page interface
  // -------------------------------------------------------

  return (
    <main className="grid min-h-screen bg-slate-950 text-white lg:grid-cols-2">

      {/* Left branding panel */}

      <section className="relative hidden flex-col justify-between overflow-hidden border-r border-slate-800 bg-slate-900/50 p-12 lg:flex">
        <div className="absolute -left-32 top-32 size-96 rounded-full bg-blue-600/10 blur-3xl" />

        <Link href="/" className="relative z-10 flex items-center gap-3">
          <div className="rounded-xl bg-blue-600 p-3">
            <Code2 size={26} />
          </div>

          <span className="text-xl font-bold tracking-tight">
            SherlskyyCommand
          </span>
        </Link>

        <div className="relative z-10 max-w-lg">
          <p className="mb-5 text-sm font-semibold uppercase tracking-[0.25em] text-blue-400">
            Developer Command Center
          </p>

          <h1 className="text-5xl font-bold leading-tight tracking-tight">
            Your projects.
            <br />
            Your systems.
            <br />
            <span className="text-blue-500">
              One command center.
            </span>
          </h1>

          <p className="mt-7 max-w-md text-base leading-8 text-slate-400">
            Access your software portfolio, manage development
            activities and keep your projects organized from
            one centralized platform.
          </p>
        </div>

        <p className="relative z-10 text-sm text-slate-500">
          SherlskyyCommand · Version {process.env.NEXT_PUBLIC_APP_VERSION}
        </p>
      </section>

      {/* Right authentication panel */}

      <section className="flex items-center justify-center px-6 py-12 sm:px-10">
        <div className="w-full max-w-md">

          <Link
            href="/"
            className="mb-10 inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-white lg:hidden"
          >
            <ArrowLeft size={16} />
            Back to homepage
          </Link>

          {/* Mobile brand */}

          <div className="mb-10 flex items-center gap-3 lg:hidden">
            <div className="rounded-xl bg-blue-600 p-3">
              <Code2 size={24} />
            </div>

            <span className="text-lg font-bold">
              SherlskyyCommand
            </span>
          </div>

          {step === "login" ? (
            <>
              <div className="mb-8">
                <div className="mb-5 flex size-12 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
                  <LockKeyhole size={24} />
                </div>

                <h2 className="text-3xl font-bold tracking-tight">
                  Welcome back
                </h2>

                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Sign in to access your command center.
                </p>
              </div>

              <form
                onSubmit={loginForm.handleSubmit(handleLogin)}
                className="space-y-5"
                noValidate
              >
                {/* Email */}

                <div>
                  <label
                    htmlFor="email"
                    className="mb-2 block text-sm font-medium text-slate-300"
                  >
                    Email address
                  </label>

                  <div className="relative">
                    <Mail
                      size={18}
                      className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500"
                    />

                    <input
                      id="email"
                      type="email"
                      autoComplete="email"
                      placeholder="you@example.com"
                      disabled={isSubmitting}
                      aria-invalid={!!loginForm.formState.errors.email}
                      {...loginForm.register("email")}
                      className="w-full rounded-xl border border-slate-700 bg-slate-900 py-3.5 pl-11 pr-4 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-60"
                    />
                  </div>

                  {loginForm.formState.errors.email && (
                    <p className="mt-2 text-xs text-red-400">
                      {loginForm.formState.errors.email.message}
                    </p>
                  )}
                </div>

                {/* Password */}

                <div>
                  <label
                    htmlFor="password"
                    className="mb-2 block text-sm font-medium text-slate-300"
                  >
                    Password
                  </label>

                  <div className="relative">
                    <LockKeyhole
                      size={18}
                      className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500"
                    />

                    <input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      placeholder="Enter your password"
                      disabled={isSubmitting}
                      aria-invalid={!!loginForm.formState.errors.password}
                      {...loginForm.register("password")}
                      className="w-full rounded-xl border border-slate-700 bg-slate-900 py-3.5 pl-11 pr-12 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-60"
                    />

                    <button
                      type="button"
                      onClick={() => setShowPassword((value) => !value)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-white"
                    >
                      {showPassword ? (
                        <EyeOff size={18} />
                      ) : (
                        <Eye size={18} />
                      )}
                    </button>
                  </div>

                  {loginForm.formState.errors.password && (
                    <p className="mt-2 text-xs text-red-400">
                      {loginForm.formState.errors.password.message}
                    </p>
                  )}
                </div>

                {/* API error */}

                {errorMessage && (
                  <div
                    role="alert"
                    className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300"
                  >
                    {errorMessage}
                  </div>
                )}

                {/* Submit */}

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSubmitting && (
                    <LoaderCircle size={18} className="animate-spin" />
                  )}

                  {isSubmitting ? "Signing in..." : "Sign in"}
                </button>
              </form>

              <p className="mt-6 text-center text-sm text-slate-400">
                Don&apos;t have an account?{" "}
                <Link
                  href="/register"
                  className="font-medium text-blue-400 transition hover:text-blue-300"
                >
                  Sign up
                </Link>
              </p>
            </>
          ) : (
            <>
              <div className="mb-8">
                <button
                  type="button"
                  onClick={() => {
                    setStep("login");
                    setErrorMessage(null);
                    mfaForm.reset();
                  }}
                  className="mb-7 inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"
                >
                  <ArrowLeft size={16} />
                  Back to sign in
                </button>

                <div className="mb-5 flex size-12 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
                  <ShieldCheck size={24} />
                </div>

                <h2 className="text-3xl font-bold tracking-tight">
                  Verify your identity
                </h2>

                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Enter the code from your authenticator app
                  or use one of your recovery codes.
                </p>
              </div>

              <form
                onSubmit={mfaForm.handleSubmit(handleMFA)}
                className="space-y-5"
                noValidate
              >
                <div>
                  <label
                    htmlFor="mfa-code"
                    className="mb-2 block text-sm font-medium text-slate-300"
                  >
                    Authentication code
                  </label>

                  <input
                    id="mfa-code"
                    type="text"
                    autoComplete="one-time-code"
                    autoFocus
                    placeholder="Enter your code"
                    disabled={isSubmitting}
                    aria-invalid={!!mfaForm.formState.errors.code}
                    {...mfaForm.register("code")}
                    className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-4 text-center text-lg tracking-[0.2em] text-white outline-none transition placeholder:text-sm placeholder:tracking-normal placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-60"
                  />

                  {mfaForm.formState.errors.code && (
                    <p className="mt-2 text-xs text-red-400">
                      {mfaForm.formState.errors.code.message}
                    </p>
                  )}
                </div>

                {errorMessage && (
                  <div
                    role="alert"
                    className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300"
                  >
                    {errorMessage}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSubmitting && (
                    <LoaderCircle size={18} className="animate-spin" />
                  )}

                  {isSubmitting ? "Verifying..." : "Verify and continue"}
                </button>
              </form>
            </>
          )}

          <p className="mt-8 text-center text-xs leading-6 text-slate-500">
            Protected access to your SherlskyyCommand workspace.
          </p>
        </div>
      </section>
    </main>
  );
}
