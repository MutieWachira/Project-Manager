
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock3,
  Code2,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Plus,
  RefreshCw,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import ProtectedRoute from "../../components/auth/protected-route";
import ProjectCreateForm from "../../components/projects/project-create-form";
import { useAuth } from "../../components/providers/auth-provider";
import WhatsNew from "../../components/whats-new";

import { getProjects } from "../../lib/project-service";
import type {
  Project,
  ProjectStatus,
} from "../../lib/project-service";

// ---------------------------------------------------------
// Project status styles
// ---------------------------------------------------------

const projectStatusStyles: Record<ProjectStatus, string> = {
  planned: "border-slate-700 bg-slate-800 text-slate-300",
  active: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
  paused: "border-amber-500/30 bg-amber-500/10 text-amber-400",
  completed: "border-blue-500/30 bg-blue-500/10 text-blue-400",
  archived: "border-slate-700 bg-slate-800 text-slate-500",
};

// ---------------------------------------------------------
// Dashboard content
// ---------------------------------------------------------

function DashboardContent() {
  const { user, logout, accessToken } = useAuth();

  // Logout state
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);

  // Project state
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [projectRefreshKey, setProjectRefreshKey] = useState(0);

  // Project creation state
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [projectSuccess, setProjectSuccess] = useState<string | null>(null);

  // -------------------------------------------------------
  // Fetch projects from the backend
  // -------------------------------------------------------

  useEffect(() => {
    let isActive = true;

    async function loadProjects() {
      if (!accessToken) {
        setProjects([]);
        setIsLoadingProjects(false);
        return;
      }

      setIsLoadingProjects(true);
      setProjectsError(null);

      try {
        const result = await getProjects(accessToken);

        if (isActive) {
          setProjects(result);
        }
      } catch {
        if (isActive) {
          setProjectsError(
            "We couldn't load your projects. Please try again.",
          );
        }
      } finally {
        if (isActive) {
          setIsLoadingProjects(false);
        }
      }
    }

    void loadProjects();

    return () => {
      isActive = false;
    };
  }, [accessToken, projectRefreshKey]);

  // -------------------------------------------------------
  // Project creation
  // -------------------------------------------------------

  function handleProjectCreated(project: Project) {
    setProjects((currentProjects) => [
      project,
      ...currentProjects.filter((item) => item.id !== project.id),
    ]);

    setIsCreatingProject(false);
    setProjectsError(null);
    setProjectSuccess(`"${project.name}" was created successfully.`);
  }

  function handleOpenProjectForm() {
    setProjectSuccess(null);
    setIsCreatingProject((current) => !current);
  }

  function handleCancelProjectCreation() {
    setIsCreatingProject(false);
  }

  // -------------------------------------------------------
  // Logout
  // -------------------------------------------------------

  async function handleLogout() {
    setIsLoggingOut(true);
    setLogoutError(null);

    try {
      await logout();
      window.location.assign("/login");
    } catch {
      setLogoutError(
        "We could not complete the server logout. Please try again.",
      );
      setIsLoggingOut(false);
    }
  }

  // -------------------------------------------------------
  // Account loading state
  // -------------------------------------------------------

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
        Loading your account details...
      </main>
    );
  }

  // -------------------------------------------------------
  // Dashboard UI
  // -------------------------------------------------------

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 lg:flex">
      {/* Sidebar */}
      <aside className="flex w-full flex-col border-b border-slate-800 bg-slate-900/70 p-5 lg:min-h-screen lg:w-64 lg:border-b-0 lg:border-r">
        <Link href="/" className="flex items-center gap-3">
          <div className="rounded-xl bg-blue-600 p-2.5">
            <Code2 size={24} />
          </div>

          <span className="text-lg font-bold tracking-tight">
            SherlskyyCommand
          </span>
        </Link>

        <div className="mt-10">
          <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Workspace
          </p>

          <Link
            href="/dashboard"
            className="flex items-center gap-3 rounded-xl bg-blue-600/15 px-3 py-3 text-sm font-medium text-blue-400"
          >
            <LayoutDashboard size={19} />
            Dashboard
          </Link>

          <Link
            href="#projects"
            className="mt-2 flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-slate-400 transition hover:bg-slate-800 hover:text-white"
          >
            <FolderKanban size={19} />
            Projects
          </Link>
        </div>

        <div className="mt-auto hidden pt-10 lg:block">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <ShieldCheck size={17} className="text-emerald-400" />
              Account security
            </div>

            <p className="mt-2 text-xs leading-5 text-slate-500">
              Your account is protected by SherlskyyCommand authentication.
            </p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="min-w-0 flex-1">
        <header className="flex flex-col gap-4 border-b border-slate-800 px-6 py-5 sm:flex-row sm:items-center sm:justify-between lg:px-10">
          <div>
            <p className="text-sm text-slate-500">
              Workspace / Overview
            </p>

            <h1 className="mt-1 text-xl font-semibold">
              Dashboard
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <WhatsNew userId={user.id} />

            <button
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:border-red-500/50 hover:text-red-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <LogOut size={17} />
              {isLoggingOut ? "Signing out..." : "Sign out"}
            </button>
          </div>
        </header>

        <div className="mx-auto max-w-7xl space-y-8 px-6 py-8 lg:px-10">
          {/* Welcome */}
          <section>
            <p className="text-sm font-medium text-blue-400">
              YOUR COMMAND CENTER
            </p>

            <h2 className="mt-2 text-3xl font-bold tracking-tight">
              Welcome, {user.full_name}
            </h2>

            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
              Your centralized workspace for managing software projects,
              development progress, and application administration.
            </p>
          </section>

          {/* Logout error */}
          {logoutError && (
            <div
              role="alert"
              className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300"
            >
              {logoutError}
            </div>
          )}

          {/* Account overview */}
          <section>
            <h3 className="mb-4 text-lg font-semibold">
              Account overview
            </h3>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {/* Account status */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">
                    Account status
                  </span>

                  <UserRound className="text-blue-400" size={20} />
                </div>

                <p className="mt-4 text-xl font-semibold">
                  {user.is_active ? "Active" : "Inactive"}
                </p>

                <p className="mt-2 text-xs text-slate-500">
                  Current account state
                </p>
              </div>

              {/* Email verification */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">
                    Email verification
                  </span>

                  {user.email_verified ? (
                    <CheckCircle2
                      className="text-emerald-400"
                      size={20}
                    />
                  ) : (
                    <Clock3
                      className="text-amber-400"
                      size={20}
                    />
                  )}
                </div>

                <p className="mt-4 text-xl font-semibold">
                  {user.email_verified ? "Verified" : "Not verified"}
                </p>

                <p className="mt-2 text-xs text-slate-500">
                  {user.email}
                </p>
              </div>

              {/* Workspace */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 md:col-span-2 xl:col-span-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">
                    Workspace
                  </span>

                  <Activity className="text-blue-400" size={20} />
                </div>

                <p className="mt-4 text-xl font-semibold">
                  Ready
                </p>

                <p className="mt-2 text-xs text-slate-500">
                  Your dashboard is connected to your account.
                </p>
              </div>
            </div>
          </section>

          {/* Projects */}
          <section
            id="projects"
            className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 sm:p-8"
          >
            {/* Project heading and actions */}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-blue-500/10 p-3 text-blue-400">
                  <FolderKanban size={24} />
                </div>

                <div>
                  <h3 className="font-semibold">
                    Project management
                  </h3>

                  <p className="text-sm text-slate-500">
                    Your software portfolio
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {!isLoadingProjects && !projectsError && (
                  <span className="text-sm text-slate-400">
                    {projects.length}{" "}
                    {projects.length === 1 ? "project" : "projects"}
                  </span>
                )}

                <button
                  type="button"
                  onClick={handleOpenProjectForm}
                  disabled={!accessToken}
                  aria-expanded={isCreatingProject}
                  aria-controls="project-creation-form"
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Plus size={17} />
                  {isCreatingProject ? "Close form" : "New project"}
                </button>
              </div>
            </div>

            <div className="mt-8 border-t border-slate-800 pt-7">
              {/* Project creation form */}
              {isCreatingProject && accessToken && (
                <div id="project-creation-form" className="mb-7">
                  <ProjectCreateForm
                    accessToken={accessToken}
                    onCreated={handleProjectCreated}
                    onCancel={handleCancelProjectCreation}
                  />
                </div>
              )}

              {/* Creation success message */}
              {projectSuccess && (
                <div
                  role="status"
                  className="mb-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-300"
                >
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={18} />
                    {projectSuccess}
                  </div>
                </div>
              )}

              {/* Loading */}
              {isLoadingProjects && (
                <div
                  role="status"
                  className="flex items-center gap-3 py-8 text-sm text-slate-400"
                >
                  <Clock3
                    size={20}
                    className="animate-pulse text-blue-400"
                  />

                  Loading your projects...
                </div>
              )}

              {/* Error */}
              {!isLoadingProjects && projectsError && (
                <div
                  role="alert"
                  className="rounded-xl border border-red-500/30 bg-red-500/10 p-5"
                >
                  <div className="flex items-center gap-3 text-red-300">
                    <AlertCircle size={20} />

                    <p className="text-sm font-medium">
                      {projectsError}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() =>
                      setProjectRefreshKey((current) => current + 1)
                    }
                    className="mt-4 inline-flex items-center gap-2 rounded-lg border border-red-500/30 px-3 py-2 text-sm text-red-300 transition hover:bg-red-500/10"
                  >
                    <RefreshCw size={15} />
                    Try again
                  </button>
                </div>
              )}

              {/* Empty state */}
              {!isLoadingProjects &&
                !projectsError &&
                projects.length === 0 && (
                  <div className="py-8 text-center">
                    <FolderKanban
                      size={36}
                      className="mx-auto text-slate-600"
                    />

                    <h4 className="mt-4 text-lg font-semibold">
                      No projects yet
                    </h4>

                    <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-400">
                      Projects you create or that are shared with you
                      will appear here. Your project management
                      workspace is connected and ready.
                    </p>

                    {!isCreatingProject && (
                      <button
                        type="button"
                        onClick={handleOpenProjectForm}
                        disabled={!accessToken}
                        className="mt-5 inline-flex items-center gap-2 rounded-xl border border-blue-500/40 px-4 py-2.5 text-sm font-medium text-blue-400 transition hover:bg-blue-500/10 disabled:opacity-50"
                      >
                        <Plus size={17} />
                        Create your first project
                      </button>
                    )}
                  </div>
                )}

              {/* Project list */}
              {!isLoadingProjects &&
                !projectsError &&
                projects.length > 0 && (
                  <div className="grid gap-4 md:grid-cols-2">
                    {projects.map((project) => (
                      <article
                        key={project.id}
                        className="rounded-xl border border-slate-800 bg-slate-950/60 p-5 transition hover:border-slate-700"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <h4 className="font-semibold text-slate-100">
                            {project.name}
                          </h4>

                          <span
                            className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-medium ${
                              projectStatusStyles[project.status]
                            }`}
                          >
                            {project.status.charAt(0).toUpperCase() +
                              project.status.slice(1)}
                          </span>
                        </div>

                        <p className="mt-3 min-h-10 text-sm leading-5 text-slate-400">
                          {project.description ||
                            "No description provided."}
                        </p>

                        <div className="mt-5 border-t border-slate-800 pt-3">
                          <p className="text-xs text-slate-500">
                            Slug:{" "}
                            <span className="font-mono text-slate-400">
                              {project.slug}
                            </span>
                          </p>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
            </div>
          </section>

          {/* Profile */}
          <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h3 className="font-semibold">
              Signed-in profile
            </h3>

            <div className="mt-5 grid gap-5 sm:grid-cols-2">
              <div>
                <p className="text-xs text-slate-500">
                  Full name
                </p>

                <p className="mt-1 text-sm font-medium">
                  {user.full_name}
                </p>
              </div>

              <div>
                <p className="text-xs text-slate-500">
                  Email address
                </p>

                <p className="mt-1 break-all text-sm font-medium">
                  {user.email}
                </p>
              </div>

              <div className="sm:col-span-2">
                <p className="text-xs text-slate-500">
                  Account ID
                </p>

                <p className="mt-1 break-all font-mono text-xs text-slate-400">
                  {user.id}
                </p>
              </div>
            </div>
          </section>

          {/* Footer */}
          <footer className="border-t border-slate-800 pt-6 text-xs text-slate-600">
            SherlskyyCommand · See What&apos;s new for the latest release
          </footer>
        </div>
      </main>
    </div>
  );
}

// ---------------------------------------------------------
// Protected dashboard page
// ---------------------------------------------------------

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
