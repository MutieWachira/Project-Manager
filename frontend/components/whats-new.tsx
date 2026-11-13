"use client";

import { useEffect, useState } from "react";
import { Sparkles, X } from "lucide-react";

import type {
  ReleaseNotes,
  ReleaseNoteSection,
} from "../lib/release-notes";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isReleaseNoteSection(value: unknown): value is ReleaseNoteSection {
  return (
    isRecord(value) &&
    typeof value.title === "string" &&
    Array.isArray(value.changes) &&
    value.changes.every((change) => typeof change === "string")
  );
}

function isReleaseNotes(value: unknown): value is ReleaseNotes {
  return (
    isRecord(value) &&
    typeof value.version === "string" &&
    (typeof value.date === "string" || value.date === null) &&
    Array.isArray(value.sections) &&
    value.sections.every(isReleaseNoteSection)
  );
}

export default function WhatsNew({ userId }: Readonly<{ userId: string }>) {
  const lastSeenVersionKey = `sherlskyycommand:last-seen-release:${userId}`;
  const [release, setRelease] = useState<ReleaseNotes | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [storageError, setStorageError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let active = true;

    async function loadReleaseNotes() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch("/api/whats-new", {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Release notes request failed (${response.status}).`);
        }

        const data: unknown = await response.json();
        if (!isReleaseNotes(data)) {
          throw new Error("The release notes response has an invalid format.");
        }

        if (!active) {
          return;
        }

        setRelease(data);

        try {
          const lastSeenVersion = window.localStorage.getItem(lastSeenVersionKey);
          setStorageError(null);

          if (lastSeenVersion === null) {
            window.localStorage.setItem(lastSeenVersionKey, data.version);
            setIsOpen(false);
          } else {
            setIsOpen(lastSeenVersion !== data.version);
          }
        } catch (storageReadError) {
          console.error(
            "Could not read the last-seen release version.",
            storageReadError,
          );
          setStorageError("We couldn't remember which release notes you've seen.");
          setIsOpen(false);
        }
      } catch (loadError) {
        console.error("Could not load release notes.", loadError);
        if (active) {
          setError("We couldn't load the latest release notes.");
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    void loadReleaseNotes();

    return () => {
      active = false;
    };
  }, [lastSeenVersionKey, retryKey]);

  function dismiss() {
    if (release) {
      try {
        window.localStorage.setItem(lastSeenVersionKey, release.version);
        setStorageError(null);
      } catch (storageWriteError) {
        console.error(
          "Could not save the last-seen release version.",
          storageWriteError,
        );
        setStorageError("We couldn't remember that you've seen this release.");
      }
    }

    setIsOpen(false);
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center justify-center gap-2 rounded-xl border border-blue-500/30 bg-blue-500/10 px-4 py-2.5 text-sm font-medium text-blue-300 transition hover:border-blue-400/60 hover:text-blue-200"
        aria-haspopup="dialog"
      >
        <Sparkles size={17} />
        What&apos;s new{release ? ` · ${release.version}` : ""}
      </button>

      {(error || storageError) && !isOpen && (
        <p role="alert" className="text-xs text-amber-300">
          {error ?? storageError}
          {error && (
            <button
              type="button"
              onClick={() => setRetryKey((current) => current + 1)}
              className="ml-2 underline underline-offset-2"
            >
              Retry
            </button>
          )}
        </p>
      )}

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="whats-new-title"
            className="w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl shadow-black/50"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-800 px-6 py-5">
              <div>
                <p className="text-sm font-medium text-blue-400">
                  SherlskyyCommand release
                </p>
                <h2
                  id="whats-new-title"
                  className="mt-1 text-2xl font-bold text-white"
                >
                  What&apos;s new
                </h2>
                {release && (
                  <p className="mt-2 text-sm text-slate-400">
                    Version {release.version}
                    {release.date ? ` · ${release.date}` : ""}
                  </p>
                )}
              </div>

              <button
                type="button"
                onClick={dismiss}
                aria-label="Close release notes"
                className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white"
              >
                <X size={20} />
              </button>
            </header>

            <div className="max-h-[60vh] overflow-y-auto px-6 py-5">
              {isLoading && (
                <p role="status" className="text-sm text-slate-400">
                  Loading release notes...
                </p>
              )}

              {!isLoading && error && (
                <div role="alert">
                  <p className="text-sm text-red-300">{error}</p>
                  <button
                    type="button"
                    onClick={() => setRetryKey((current) => current + 1)}
                    className="mt-3 text-sm font-medium text-blue-300 hover:text-blue-200"
                  >
                    Try again
                  </button>
                </div>
              )}

              {!isLoading && !error && release && (
                <div className="space-y-6">
                  {release.sections.length === 0 ? (
                    <p className="text-sm text-slate-400">
                      This release has no change details yet.
                    </p>
                  ) : (
                    release.sections.map((section) => (
                      <section key={section.title}>
                        <h3 className="font-semibold text-slate-100">
                          {section.title}
                        </h3>
                        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-slate-300 marker:text-blue-400">
                          {section.changes.map((change, index) => (
                            <li key={`${section.title}-${index}`}>{change}</li>
                          ))}
                        </ul>
                      </section>
                    ))
                  )}
                  {storageError && (
                    <p role="status" className="text-xs text-amber-300">
                      {storageError}
                    </p>
                  )}
                </div>
              )}
            </div>

            <footer className="flex justify-end border-t border-slate-800 px-6 py-4">
              <button
                type="button"
                onClick={dismiss}
                className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
              >
                Got it
              </button>
            </footer>
          </section>
        </div>
      )}
    </>
  );
}
