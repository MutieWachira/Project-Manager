"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ArrowUpRight, Check, Sparkles, X } from "lucide-react";

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
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

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

  useEffect(() => {
    const dialog = dialogRef.current;

    if (!isOpen || !dialog) {
      return;
    }

    const previousBodyOverflow = document.body.style.overflow;

    dialog.showModal();
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    return () => {
      if (dialog.open) {
        dialog.close();
      }

      document.body.style.overflow = previousBodyOverflow;
      triggerRef.current?.focus();
    };
  }, [isOpen]);

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
        ref={triggerRef}
        type="button"
        onClick={() => setIsOpen(true)}
        className="group inline-flex items-center justify-center gap-2.5 rounded-xl border border-blue-400/20 bg-gradient-to-r from-blue-500/10 to-indigo-500/10 px-4 py-2.5 text-sm font-semibold text-blue-100 shadow-sm shadow-blue-950/20 transition hover:border-blue-300/40 hover:from-blue-500/20 hover:to-indigo-500/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-400"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-controls="whats-new-dialog"
      >
        <Sparkles
          size={16}
          className="text-blue-300 transition group-hover:rotate-12 group-hover:scale-110"
        />
        <span>What&apos;s new</span>
        {release && (
          <span className="rounded-full border border-blue-300/15 bg-blue-300/10 px-2 py-0.5 text-[10px] font-bold tracking-wide text-blue-200">
            v{release.version}
          </span>
        )}
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

      {isOpen &&
        typeof document !== "undefined" &&
        createPortal(
          <dialog
            ref={dialogRef}
            id="whats-new-dialog"
            aria-labelledby="whats-new-title"
            aria-describedby="whats-new-description"
            className="fixed inset-0 m-0 h-dvh max-h-none w-screen max-w-none overflow-y-auto border-0 bg-transparent p-0 text-slate-100 backdrop:bg-slate-950/80 backdrop:backdrop-blur-md"
            onCancel={(event) => {
              event.preventDefault();
              dismiss();
            }}
            onClick={(event) => {
              if (event.target === event.currentTarget) {
                dismiss();
              }
            }}
          >
            <div className="flex min-h-full items-center justify-center p-3 sm:p-6">
              <section className="relative my-auto flex max-h-[calc(100dvh-1.5rem)] w-full max-w-3xl flex-col overflow-hidden rounded-3xl border border-white/10 bg-[#0b1423] shadow-2xl shadow-black/60 sm:max-h-[calc(100dvh-3rem)]">
                <header className="relative isolate shrink-0 overflow-hidden border-b border-white/[0.08] bg-gradient-to-br from-blue-500/[0.16] via-indigo-500/[0.08] to-transparent px-5 py-6 sm:px-8 sm:py-8">
                  <div className="pointer-events-none absolute -right-12 -top-24 -z-10 h-64 w-64 rounded-full bg-blue-400/20 blur-3xl" />
                  <div className="flex items-start justify-between gap-5">
                    <div className="min-w-0">
                      <div className="inline-flex items-center gap-2 rounded-full border border-blue-300/20 bg-blue-400/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-blue-200">
                        <Sparkles size={13} />
                        Product updates
                      </div>
                      <h2
                        id="whats-new-title"
                        className="mt-4 text-3xl font-bold tracking-tight text-white sm:text-4xl"
                      >
                        What&apos;s new
                      </h2>
                      <p
                        id="whats-new-description"
                        className="mt-2 max-w-xl text-sm leading-6 text-slate-300 sm:text-base"
                      >
                        A quick look at the latest improvements to your
                        workspace.
                      </p>
                      {release && (
                        <div className="mt-5 flex flex-wrap items-center gap-2 text-xs font-medium text-slate-300">
                          <span className="rounded-lg border border-white/10 bg-slate-950/40 px-2.5 py-1.5 text-blue-200">
                            Web v{release.version}
                          </span>
                          {release.date && (
                            <span className="text-slate-400">
                              Released {release.date}
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    <button
                      ref={closeButtonRef}
                      type="button"
                      onClick={dismiss}
                      aria-label="Close release notes"
                      className="shrink-0 rounded-xl border border-white/10 bg-slate-950/30 p-2.5 text-slate-400 transition hover:border-white/20 hover:bg-white/10 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-400"
                    >
                      <X size={19} />
                    </button>
                  </div>
                </header>

                <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-8 sm:py-7">
                  {isLoading && (
                    <p role="status" className="text-sm text-slate-400">
                      Loading release notes...
                    </p>
                  )}

                  {!isLoading && error && (
                    <div
                      role="alert"
                      className="rounded-2xl border border-red-400/20 bg-red-400/[0.06] p-5"
                    >
                      <p className="text-sm text-red-200">{error}</p>
                      <button
                        type="button"
                        onClick={() => setRetryKey((current) => current + 1)}
                        className="mt-3 text-sm font-semibold text-blue-300 hover:text-blue-200"
                      >
                        Try again
                      </button>
                    </div>
                  )}

                  {!isLoading && !error && release && (
                    <div className="space-y-7">
                      {release.sections.length === 0 ? (
                        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] px-5 py-8 text-center">
                          <Sparkles className="mx-auto text-blue-300" size={22} />
                          <p className="mt-3 text-sm text-slate-300">
                            This release has no change details yet.
                          </p>
                        </div>
                      ) : (
                        release.sections.map((section) => (
                          <section key={section.title}>
                            <h3 className="text-xs font-bold uppercase tracking-[0.15em] text-slate-400">
                              {section.title}
                            </h3>
                            <ul className="mt-3 space-y-2.5">
                              {section.changes.map((change, index) => (
                                <li
                                  key={`${section.title}-${index}`}
                                  className="flex gap-3 rounded-2xl border border-white/[0.07] bg-white/[0.025] px-4 py-3.5 text-sm leading-6 text-slate-200 transition hover:border-blue-300/15 hover:bg-blue-300/[0.04]"
                                >
                                  <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-400/10 text-emerald-300">
                                    <Check size={12} strokeWidth={3} />
                                  </span>
                                  <span>{change}</span>
                                </li>
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

                <footer className="flex shrink-0 items-center justify-between gap-4 border-t border-white/[0.08] bg-slate-950/30 px-5 py-4 sm:px-8">
                  <p className="hidden text-xs text-slate-500 sm:block">
                    Thanks for building with us.
                  </p>
                  <button
                    type="button"
                    onClick={dismiss}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-950/40 transition hover:bg-blue-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-300 sm:w-auto"
                  >
                    Got it
                    <ArrowUpRight size={16} />
                  </button>
                </footer>
              </section>
            </div>
          </dialog>,
          document.body,
        )}
    </>
  );
}
