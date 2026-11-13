
import { Suspense } from "react";
import VerificationForm from "./verification-form";

interface VerifyEmailPageProps {
  searchParams: Promise<{
    token?: string | string[];
  }>;
}

async function VerificationPageContent({
  searchParams,
}: VerifyEmailPageProps) {
  const params = await searchParams;

  const token =
    typeof params.token === "string" ? params.token : null;

  return <VerificationForm token={token} />;
}

export default function VerifyEmailPage({
  searchParams,
}: VerifyEmailPageProps) {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center bg-[#080d18] px-6 text-slate-100">
          <p className="text-slate-400">
            Loading email verification...
          </p>
        </main>
      }
    >
      <VerificationPageContent searchParams={searchParams} />
    </Suspense>
  );
}
