
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Activity,
  AlertCircle,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Code2,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Plus,
  RefreshCw,
  Search,
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

const statusStyles: Record<ProjectStatus, string> = {
  planned: "border-slate-600 bg-slate-800 text-slate-300",
  active: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
  paused: "border-amber-500/30 bg-amber-500/10 text-amber-400",
  completed: "border-blue-500/30 bg-blue-500/10 text-blue-400",
  archived: "border-slate-700 bg-slate-800 text-slate-400",
};

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }

  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function DashboardContent() {
  const { user, logout, accessToken } = useAuth();
  const router = useRouter();

  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [projectRefreshKey, setProjectRefreshKey] = useState(0);

  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [projectSuccess, setProjectSuccess] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const appVersion = process.env.NEXT_PUBLIC_APP_VERSION ?? "Unknown";

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

  function handleProjectCreated(project: Project) {
    setProjects((current) => [
      project,
      ...current.filter((item) => item.id !== project.id),
    ]);

    setIsCreatingProject(false);
    setProjectsError(null);
    setProjectSuccess(`"${project.name}" was created successfully.`);
  }

  function handleOpenProjectForm() {
    setProjectSuccess(null);
    setIsCreatingProject((current) => !current);
  }

  async function handleLogout() {
    setIsLoggingOut(true);
    setLogoutError(null);

    try {
      await logout();
      router.replace("/login");
    } catch {
      setLogoutError(
        "We could not complete the server logout. Please try again.",
      );
      setIsLoggingOut(false);
    }
  }

  const totalProjects = projects.length;
  const activeProjects = projects.filter(
    (project) => project.status === "active",
  ).length;
  const plannedProjects = projects.filter(
    (project) => project.status === "planned",
  ).length;
  const completedProjects = projects.filter(
    (project) => project.status === "completed",
  ).length;

  const filteredProjects = projects.filter((project) => {
    const query = searchQuery.trim().toLowerCase();

    if (!query) return true;

    return (
      project.name.toLowerCase().includes(query) ||
      project.slug.toLowerCase().includes(query) ||
      (project.description ?? "").toLowerCase().includes(query)
    );
  });

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
        <div className="text-center">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <p className="text-sm">Loading your workspace...</p>
        </div>
      </main>
    );
  }

  const statistics = [
    {
      label: "Total projects",
      value: totalProjects,
      description: "Projects in your workspace",
      icon: FolderKanban,
      color: "text-blue-400",
      background: "bg-blue-500/10",
    },
    {
      label: "Active projects",
      value: activeProjects,
      description: "Currently in progress",
      icon: Activity,
      color: "text-emerald-400",
      background: "bg-emerald-500/10",
    },
    {
      label: "Planned projects",
      value: plannedProjects,
      description: "Waiting to get started",
      icon: Clock3,
      color: "text-amber-400",
      background: "bg-amber-500/10",
    },
    {
      label: "Completed",
      value: completedProjects,
      description: "Successfully completed",
      icon: CheckCircle2,
      color: "text-violet-400",
      background: "bg-violet-500/10",
    },
  ];

  return (
    <div className="min-h-screen bg-[#09111f] text-slate-100 lg:flex">
      {/* Sidebar */}
      <aside className="flex w-full shrink-0 flex-col border-b border-slate-800/80 bg-[#0c1627] p-5 lg:sticky lg:top-0 lg:h-screen lg:w-72 lg:border-b-0 lg:border-r">
        <Link href="/" className="flex items-center gap-3">
          <div className="rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 p-2.5 text-white shadow-lg shadow-blue-950/50 ring-1 ring-white/15">
            <Code2 size={23} />
          </div>

          <div>
            <p className="text-base font-bold tracking-tight">
              SherlskyyCommand
            </p>
            <p className="text-[11px] text-slate-500">
              Project workspace
            </p>
          </div>
        </Link>

        <div className="mt-9">
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
            Workspace
          </p>

          <Link
            href="/dashboard"
            className="flex items-center gap-3 rounded-xl border border-blue-500/20 bg-blue-500/10 px-3 py-3 text-sm font-semibold text-blue-400"
          >
            <LayoutDashboard size={18} />
            Overview
          </Link>

          <Link
            href="#projects"
            className="mt-2 flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-slate-400 transition hover:bg-slate-800/70 hover:text-white"
          >
            <FolderKanban size={18} />
            Projects
          </Link>
        </div>

        <div className="mt-8 border-t border-slate-800 pt-6">
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
            Account
          </p>

          <div className="flex items-center gap-3 rounded-xl bg-slate-900/70 p-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600/20 text-sm font-bold text-blue-400">
              {user.full_name.charAt(0).toUpperCase()}
            </div>

            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-200">
                {user.full_name}
              </p>
              <p className="truncate text-xs text-slate-500">
                {user.email}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-auto hidden pt-8 lg:block">
          <div className="rounded-xl border border-emerald-500/15 bg-emerald-500/5 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-emerald-400">
              <ShieldCheck size={17} />
              Account protected
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              Your workspace is protected by SherlskyyCommand authentication.
            </p>
          </div>

          <p className="mt-5 text-center text-[10px] text-slate-600">
            SherlskyyCommand
          </p>
        </div>
      </aside>

      {/* Main workspace */}
      <main className="min-w-0 flex-1 bg-[radial-gradient(ellipse_at_top_right,_rgba(37,99,235,0.08),_transparent_35%)]">
        {/* Top navigation */}
        <header className="flex flex-col gap-4 border-b border-slate-800/80 bg-[#0b1423]/80 px-5 py-4 backdrop-blur-sm sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-10">
          <div>
            <p className="text-xs text-slate-500">
              Workspace <span className="mx-1">/</span> Overview
            </p>
            <h1 className="mt-1 text-lg font-semibold text-white">
              Dashboard
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <WhatsNew userId={user.id} />

            <button
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:border-red-500/40 hover:text-red-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <LogOut size={16} />
              {isLoggingOut ? "Signing out..." : "Sign out"}
            </button>
          </div>
        </header>

        <div className="mx-auto max-w-7xl space-y-8 px-5 py-8 sm:px-8 lg:px-10 lg:py-10">
          {/* Welcome section */}
          <section className="relative overflow-hidden rounded-3xl border border-blue-400/15 bg-gradient-to-br from-[#173a68] via-[#122a4b] to-[#0e1d34] p-6 shadow-2xl shadow-slate-950/20 sm:p-8">
            <div className="pointer-events-none absolute -right-16 -top-24 h-64 w-64 rounded-full bg-blue-400/15 blur-3xl" />
            <div className="pointer-events-none absolute bottom-0 right-10 h-40 w-40 rounded-full border border-blue-300/10" />

            <div className="relative max-w-2xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-blue-400/20 bg-blue-400/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.16em] text-blue-300">
                <Activity size={13} />
                Your command center
              </div>

              <h2 className="mt-5 text-2xl font-bold tracking-tight text-white sm:text-3xl">
                Welcome back, {user.full_name}
              </h2>

              <p className="mt-3 text-sm leading-6 text-slate-300">
                Manage your projects, monitor progress, and keep your work
                organized from one central workspace.
              </p>

              <button
                type="button"
                onClick={handleOpenProjectForm}
                disabled={!accessToken}
                className="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-950/40 transition hover:bg-blue-500 disabled:opacity-50"
              >
                <Plus size={17} />
                Create a project
              </button>
            </div>
          </section>

          {/* Error messages */}
          {logoutError && (
            <div
              role="alert"
              className="flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-300"
            >
              <AlertCircle size={18} />
              {logoutError}
            </div>
          )}

          {/* Statistics */}
          <section>
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-white">
                  Workspace overview
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  A live summary of your projects
                </p>
              </div>

              <button
                type="button"
                onClick={() =>
                  setProjectRefreshKey((current) => current + 1)
                }
                disabled={isLoadingProjects}
                aria-label="Refresh project statistics"
                className="rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-slate-400 transition hover:border-slate-600 hover:text-white disabled:opacity-50"
              >
                <RefreshCw
                  size={16}
                  className={isLoadingProjects ? "animate-spin" : ""}
                />
              </button>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {statistics.map((stat) => {
                const Icon = stat.icon;

                return (
                  <article
                    key={stat.label}
                    className="rounded-2xl border border-slate-800/90 bg-[#101b2d]/90 p-5 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-slate-600 hover:shadow-xl hover:shadow-slate-950/20"
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-slate-400">
                        {stat.label}
                      </p>
                      <div className={`rounded-xl p-2.5 ${stat.background}`}>
                        <Icon size={19} className={stat.color} />
                      </div>
                    </div>

                    <p className="mt-5 text-3xl font-bold tracking-tight text-white tabular-nums">
                      {isLoadingProjects ? "—" : stat.value}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      {stat.description}
                    </p>
                  </article>
                );
              })}
            </div>
          </section>

          {/* Projects */}
          <section
            id="projects"
            className="scroll-mt-6 rounded-3xl border border-slate-800/90 bg-[#101b2d]/90 p-5 shadow-sm sm:p-7"
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-blue-500/10 p-3 text-blue-400">
                  <FolderKanban size={21} />
                </div>

                <div>
                  <h3 className="font-semibold text-white">
                    Your projects
                  </h3>
                  <p className="mt-1 text-xs text-slate-500">
                    Manage projects created by or shared with you
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={handleOpenProjectForm}
                disabled={!accessToken}
                aria-expanded={isCreatingProject}
                aria-controls="project-creation-form"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50"
              >
                <Plus size={17} />
                {isCreatingProject ? "Close form" : "New project"}
              </button>
            </div>

            {/* Project creation form */}
            {isCreatingProject && accessToken && (
              <div id="project-creation-form" className="mt-6 border-t border-slate-800 pt-6">
                <ProjectCreateForm
                  accessToken={accessToken}
                  onCreated={handleProjectCreated}
                  onCancel={() => setIsCreatingProject(false)}
                />
              </div>
            )}

            {projectSuccess && (
              <div
                role="status"
                className="mt-6 flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-300"
              >
                <CheckCircle2 size={18} />
                {projectSuccess}
              </div>
            )}

            {/* Search */}
            <div className="mt-7">
              <label htmlFor="project-search" className="sr-only">
                Search projects
              </label>

              <div className="relative max-w-md">
                <Search
                  size={17}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"
                />
                <input
                  id="project-search"
                  type="search"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Search projects by name or description..."
                  className="w-full rounded-xl border border-slate-700 bg-slate-950/70 py-3 pl-10 pr-4 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10"
                />
              </div>
            </div>

            <div className="mt-6 border-t border-slate-800 pt-6">
              {/* Loading */}
              {isLoadingProjects && (
                <div
                  role="status"
                  className="flex items-center gap-3 py-10 text-sm text-slate-400"
                >
                  <RefreshCw size={18} className="animate-spin text-blue-400" />
                  Loading your projects...
                </div>
              )}

              {/* Error */}
              {!isLoadingProjects && projectsError && (
                <div
                  role="alert"
                  className="rounded-xl border border-red-500/20 bg-red-500/10 p-5"
                >
                  <div className="flex items-center gap-3 text-sm text-red-300">
                    <AlertCircle size={19} />
                    {projectsError}
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

              {/* Empty workspace */}
              {!isLoadingProjects &&
                !projectsError &&
                projects.length === 0 && (
                  <div className="py-12 text-center">
                    <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-800/80 text-slate-400">
                      <FolderKanban size={28} />
                    </div>

                    <h4 className="mt-5 font-semibold text-white">
                      Your workspace is ready
                    </h4>

                    <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-400">
                      You haven&apos;t added any projects yet. Create your first
                      project to get started.
                    </p>

                    {!isCreatingProject && (
                      <button
                        type="button"
                        onClick={handleOpenProjectForm}
                        className="mt-5 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
                      >
                        <Plus size={16} />
                        Create your first project
                      </button>
                    )}
                  </div>
                )}

              {/* No search results */}
              {!isLoadingProjects &&
                !projectsError &&
                projects.length > 0 &&
                filteredProjects.length === 0 && (
                  <div className="py-10 text-center">
                    <Search size={27} className="mx-auto text-slate-500" />
                    <h4 className="mt-4 font-semibold text-white">
                      No matching projects
                    </h4>
                    <p className="mt-2 text-sm text-slate-500">
                      Try another project name or search term.
                    </p>
                  </div>
                )}

              {/* Project cards */}
              {!isLoadingProjects &&
                !projectsError &&
                filteredProjects.length > 0 && (
                  <div className="grid gap-4 md:grid-cols-2">
                    {filteredProjects.map((project) => (
                      <Link
                        href={`/dashboard/projects/${project.id}`}
                        key={project.id}
                        className="group block rounded-2xl border border-slate-800 bg-[#0c1627]/70 p-5 transition duration-200 hover:-translate-y-0.5 hover:border-blue-500/40 hover:bg-[#0c1627] hover:shadow-lg hover:shadow-slate-950/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex min-w-0 items-center gap-3">
                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
                              <Code2 size={19} />
                            </div>

                            <div className="min-w-0">
                              <h4 className="truncate font-semibold text-slate-100">
                                {project.name}
                              </h4>
                              <p className="mt-1 truncate font-mono text-[11px] text-slate-500">
                                {project.slug}
                              </p>
                            </div>
                          </div>

                          <span
                            className={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-semibold capitalize ${statusStyles[project.status]}`}
                          >
                            {project.status}
                          </span>
                        </div>

                        <p className="mt-5 min-h-10 text-sm leading-5 text-slate-400">
                          {project.description || "No description provided."}
                        </p>

                        <div className="mt-5 flex items-center justify-between border-t border-slate-800 pt-4">
                          <div className="flex items-center gap-2 text-xs text-slate-500">
                            <CalendarDays size={14} />
                            Updated {formatDate(project.updated_at)}
                          </div>

                          <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-400 transition group-hover:text-blue-300">
                            Project
                            <ArrowUpRight size={14} />
                          </span>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
            </div>
          </section>

          {/* Account information */}
          <section className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
            <div className="rounded-3xl border border-slate-800/90 bg-[#101b2d]/90 p-6 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-blue-500/10 p-3 text-blue-400">
                  <UserRound size={20} />
                </div>
                <div>
                  <h3 className="font-semibold text-white">
                    Account information
                  </h3>
                  <p className="mt-1 text-xs text-slate-500">
                    Your signed-in account details
                  </p>
                </div>
              </div>

              <div className="mt-6 grid gap-5 sm:grid-cols-2">
                <div>
                  <p className="text-xs text-slate-500">Full name</p>
                  <p className="mt-1 text-sm font-medium text-slate-200">
                    {user.full_name}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-500">Email address</p>
                  <p className="mt-1 break-all text-sm font-medium text-slate-200">
                    {user.email}
                  </p>
                </div>

                <div className="sm:col-span-2">
                  <p className="text-xs text-slate-500">Account ID</p>
                  <p className="mt-1 break-all font-mono text-xs text-slate-400">
                    {user.id}
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800/90 bg-[#101b2d]/90 p-6 shadow-sm">
              <h3 className="font-semibold text-white">Account status</h3>

              <div className="mt-5 space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-slate-400">
                    Account
                  </span>
                  <span className={user.is_active ? "text-emerald-400" : "text-red-400"}>
                    {user.is_active ? "Active" : "Inactive"}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-slate-400">
                    Email verification
                  </span>
                  <span className={user.email_verified ? "text-emerald-400" : "text-amber-400"}>
                    {user.email_verified ? "Verified" : "Pending"}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-slate-400">
                    Workspace
                  </span>
                  <span className="text-emerald-400">Connected</span>
                </div>
              </div>
            </div>
          </section>

          <footer className="border-t border-slate-800 py-5 text-center text-xs text-slate-600">
            SherlskyyCommand v{appVersion} · Built to keep your work organized.
          </footer>
        </div>
      </main>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
