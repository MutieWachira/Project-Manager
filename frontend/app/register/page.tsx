"use client";

import { useState } from "react";
import Link from "next/link";
import axios from "axios";
import {
  ArrowLeft,
  CheckCircle2,
  Code2,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  Mail,
  UserRound,
} from "lucide-react";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { useAuth } from "../../components/providers/auth-provider";

// ---------------------------------------------------------
// Registration validation
// ---------------------------------------------------------

const registrationSchema = z
  .object({
    full_name: z
      .string()
      .trim()
      .min(2, "Your name must contain at least 2 characters.")
      .max(150, "Your name cannot exceed 150 characters."),

    email: z
      .string()
      .trim()
      .email("Enter a valid email address."),

    password: z
      .string()
      .min(12, "Password must contain at least 12 characters.")
      .max(128, "Password cannot exceed 128 characters."),

    confirm_password: z.string(),
  })
  .refine((values) => values.password === values.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });

type RegistrationFormValues = z.infer<typeof registrationSchema>;

// ---------------------------------------------------------
// API error handling
// ---------------------------------------------------------

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

    if (error.response.status === 422) {
      return "Some registration details are invalid. Please review your information.";
    }
  }

  return "Registration could not be completed. Please try again.";
}

// ---------------------------------------------------------
// Registration page
// ---------------------------------------------------------

export default function RegisterPage() {
  const { register } = useAuth();

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [registrationComplete, setRegistrationComplete] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const {
    register: registerField,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegistrationFormValues>({
    resolver: zodResolver(registrationSchema),
    defaultValues: {
      full_name: "",
      email: "",
      password: "",
      confirm_password: "",
    },
  });

  async function handleRegistration(values: RegistrationFormValues) {
    setErrorMessage("");

    try {
      await register({
        full_name: values.full_name.trim(),
        email: values.email.trim().toLowerCase(),
        password: values.password,
      });

      setRegistrationComplete(true);
    } catch (error: unknown) {
      setErrorMessage(getErrorMessage(error));
    }
  }

  return (
    <main className="min-h-screen bg-[#080d18] text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-7xl">
        {/* Brand panel */}
        <section className="relative hidden w-1/2 flex-col justify-between overflow-hidden border-r border-white/10 bg-[#0d1526] p-12 lg:flex">
          <div className="absolute -left-32 top-1/4 h-96 w-96 rounded-full bg-blue-600/10 blur-3xl" />
          <div className="absolute -right-20 bottom-0 h-80 w-80 rounded-full bg-indigo-600/10 blur-3xl" />

          <Link href="/" className="relative flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500 text-white">
              <Code2 size={24} />
            </div>
            <span className="text-xl font-semibold tracking-tight">
              SherlskyyCommand
            </span>
          </Link>

          <div className="relative max-w-lg">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-blue-400/20 bg-blue-400/10 px-4 py-2 text-sm text-blue-300">
              <LockKeyhole size={15} />
              Secure account creation
            </div>

            <h1 className="text-5xl font-bold leading-tight tracking-tight">
              One command centre.
              <span className="mt-2 block text-blue-400">
                Every project.
              </span>
            </h1>

            <p className="mt-6 max-w-md text-lg leading-8 text-slate-400">
              Create your account and bring your development projects,
              workflows, and administration into one organized workspace.
            </p>

            <div className="mt-10 space-y-5">
              {[
                "Centralize your software projects",
                "Track development progress",
                "Manage project administration",
              ].map((item) => (
                <div key={item} className="flex items-center gap-3 text-slate-300">
                  <CheckCircle2 size={19} className="text-blue-400" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          <p className="relative text-sm text-slate-500">
            Your projects. Your command centre.
          </p>
        </section>

        {/* Registration form */}
        <section className="flex w-full items-center justify-center px-6 py-12 lg:w-1/2 lg:px-12">
          <div className="w-full max-w-md">
            <Link
              href="/"
              className="mb-10 inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"
            >
              <ArrowLeft size={16} />
              Back to home
            </Link>

            <div className="mb-8 flex items-center gap-3 lg:hidden">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500">
                <Code2 size={22} />
              </div>
              <span className="text-lg font-semibold">
                SherlskyyCommand
              </span>
            </div>

            {registrationComplete ? (
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-8">
                <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10">
                  <Mail size={28} className="text-emerald-400" />
                </div>

                <h1 className="text-3xl font-bold tracking-tight">
                  Check your email
                </h1>

                <p className="mt-4 leading-7 text-slate-400">
                  Your registration request has been received. If your
                  registration can be completed, you'll receive an email
                  with instructions to verify your email address.
                </p>

                <p className="mt-4 text-sm text-slate-500">
                  Check your inbox and spam folder. You must verify your
                  email before signing in.
                </p>

                <Link
                  href="/login"
                  className="mt-8 flex w-full items-center justify-center rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white transition hover:bg-blue-500"
                >
                  Go to sign in
                </Link>
              </div>
            ) : (
              <>
                <div className="mb-8">
                  <p className="mb-3 text-sm font-medium uppercase tracking-[0.2em] text-blue-400">
                    Get started
                  </p>

                  <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                    Create your account
                  </h1>

                  <p className="mt-3 text-slate-400">
                    Enter your details to create your workspace account.
                  </p>
                </div>

                <form
                  onSubmit={handleSubmit(handleRegistration)}
                  className="space-y-5"
                  noValidate
                >
                  {/* Full name */}
                  <div>
                    <label
                      htmlFor="full_name"
                      className="mb-2 block text-sm font-medium text-slate-300"
                    >
                      Full name
                    </label>

                    <div className="relative">
                      <UserRound
                        size={18}
                        className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500"
                      />

                      <input
                        id="full_name"
                        type="text"
                        autoComplete="name"
                        placeholder="Enter your full name"
                        disabled={isSubmitting}
                        {...registerField("full_name")}
                        className="w-full rounded-xl border border-white/10 bg-white/[0.04] py-3.5 pl-12 pr-4 text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50"
                      />
                    </div>

                    {errors.full_name && (
                      <p className="mt-2 text-sm text-red-400">
                        {errors.full_name.message}
                      </p>
                    )}
                  </div>

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
                        {...registerField("email")}
                        className="w-full rounded-xl border border-white/10 bg-white/[0.04] py-3.5 pl-12 pr-4 text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50"
                      />
                    </div>

                    {errors.email && (
                      <p className="mt-2 text-sm text-red-400">
                        {errors.email.message}
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
                        autoComplete="new-password"
                        placeholder="At least 12 characters"
                        disabled={isSubmitting}
                        {...registerField("password")}
                        className="w-full rounded-xl border border-white/10 bg-white/[0.04] py-3.5 pl-12 pr-12 text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50"
                      />

                      <button
                        type="button"
                        onClick={() => setShowPassword((current) => !current)}
                        aria-label={showPassword ? "Hide password" : "Show password"}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-white"
                      >
                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>

                    {errors.password && (
                      <p className="mt-2 text-sm text-red-400">
                        {errors.password.message}
                      </p>
                    )}
                  </div>

                  {/* Confirm password */}
                  <div>
                    <label
                      htmlFor="confirm_password"
                      className="mb-2 block text-sm font-medium text-slate-300"
                    >
                      Confirm password
                    </label>

                    <div className="relative">
                      <LockKeyhole
                        size={18}
                        className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500"
                      />

                      <input
                        id="confirm_password"
                        type={showConfirmPassword ? "text" : "password"}
                        autoComplete="new-password"
                        placeholder="Enter your password again"
                        disabled={isSubmitting}
                        {...registerField("confirm_password")}
                        className="w-full rounded-xl border border-white/10 bg-white/[0.04] py-3.5 pl-12 pr-12 text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50"
                      />

                      <button
                        type="button"
                        onClick={() =>
                          setShowConfirmPassword((current) => !current)
                        }
                        aria-label={
                          showConfirmPassword
                            ? "Hide confirmation password"
                            : "Show confirmation password"
                        }
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-white"
                      >
                        {showConfirmPassword ? (
                          <EyeOff size={18} />
                        ) : (
                          <Eye size={18} />
                        )}
                      </button>
                    </div>

                    {errors.confirm_password && (
                      <p className="mt-2 text-sm text-red-400">
                        {errors.confirm_password.message}
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

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3.5 font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSubmitting ? (
                      <>
                        <LoaderCircle size={18} className="animate-spin" />
                        Creating account...
                      </>
                    ) : (
                      "Create account"
                    )}
                  </button>
                </form>

                <p className="mt-8 text-center text-sm text-slate-400">
                  Already have an account?{" "}
                  <Link
                    href="/login"
                    className="font-semibold text-blue-400 transition hover:text-blue-300"
                  >
                    Sign in
                  </Link>
                </p>
              </>
            )}

            <p className="mt-10 text-center text-xs text-slate-600">
              SherlskyyCommand · Secure project management
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
