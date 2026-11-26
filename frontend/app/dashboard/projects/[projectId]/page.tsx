"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import axios from "axios";
import {
  Activity,
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Code2,
  ExternalLink,
  FolderKanban,
  Globe,
  LoaderCircle,
  Plus,
  RefreshCw,
  Server,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";

import ProtectedRoute from "../../../../components/auth/protected-route";
import { useAuth } from "../../../../components/providers/auth-provider";

import {
  createProjectEnvironment,
  createProjectIntegration,
  deactivateProjectEnvironment,
  disconnectProjectIntegration,
  getProject,
  getProjectEnvironments,
  getProjectIntegrations,
  startProjectGitHubInstallation,
  updateProjectEnvironment,
  updateProjectIntegration,
} from "../../../../lib/project-service";

import type {
  EnvironmentCreateInput,
  EnvironmentUpdateInput,
  IntegrationCreateInput,
  IntegrationUpdateInput,
  Project,
  ProjectEnvironment,
  ProjectIntegration,
} from "../../../../lib/project-service";

// ---------------------------------------------------------
// Helpers
// ---------------------------------------------------------

const environmentTypes: ProjectEnvironment["environment_type"][] = [
  "development",
  "staging",
  "production",
  "custom",
];

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unavailable";
  }

  return date.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;

    if (status === 403) {
      return "You can view this project, but you do not have permission to manage its resources.";
    }

    if (status === 404) {
      return "The project or requested resource could not be found, or you do not have access to it.";
    }

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item: { msg?: string }) => item.msg ?? "Invalid input")
        .join(", ");
    }

    if (!error.response) {
      return "Unable to reach the backend. Check your connection and try again.";
    }
  }

  return "Something went wrong. Please try again.";
}

const typeStyles: Record<ProjectEnvironment["environment_type"], string> = {
  development: "border-blue-500/30 bg-blue-500/10 text-blue-300",
  staging: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  production: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  custom: "border-purple-500/30 bg-purple-500/10 text-purple-300",
};

interface EnvironmentFormState {
  name: string;
  environment_type: ProjectEnvironment["environment_type"];
  description: string;
  base_url: string;
  is_primary: boolean;
}

const emptyForm: EnvironmentFormState = {
  name: "",
  environment_type: "development",
  description: "",
  base_url: "",
  is_primary: false,
};

interface IntegrationFormState {
  name: string;
  integration_type: ProjectIntegration["integration_type"];
  environment_id: string;
  external_reference: string;
}

const emptyIntegrationForm: IntegrationFormState = {
  name: "",
  integration_type: "github",
  environment_id: "",
  external_reference: "",
};

// ---------------------------------------------------------
// Project workspace
// ---------------------------------------------------------

function ProjectWorkspaceContent() {
  const params = useParams<{ projectId: string }>();
  const { accessToken } = useAuth();

  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [environments, setEnvironments] = useState<ProjectEnvironment[]>([]);
  const [integrations, setIntegrations] = useState<ProjectIntegration[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [environmentError, setEnvironmentError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingEnvironment, setEditingEnvironment] =
    useState<ProjectEnvironment | null>(null);
  const [form, setForm] = useState<EnvironmentFormState>(emptyForm);
  const [isSaving, setIsSaving] = useState(false);
  const [deactivatingId, setDeactivatingId] = useState<string | null>(null);
  const [integrationError, setIntegrationError] = useState<string | null>(null);
  const [integrationSuccess, setIntegrationSuccess] = useState<string | null>(null);
  const [isIntegrationFormOpen, setIsIntegrationFormOpen] = useState(false);
  const [editingIntegration, setEditingIntegration] = useState<ProjectIntegration | null>(null);
  const [integrationForm, setIntegrationForm] = useState<IntegrationFormState>(emptyIntegrationForm);
  const [isSavingIntegration, setIsSavingIntegration] = useState(false);
  const [disconnectingIntegrationId, setDisconnectingIntegrationId] = useState<string | null>(null);
  const [installingGitHubIntegrationId, setInstallingGitHubIntegrationId] = useState<string | null>(null);

  const loadWorkspace = useCallback(async (refresh = false) => {
    if (!accessToken || !projectId) {
      return;
    }

    if (refresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    setPageError(null);
    setEnvironmentError(null);

    try {
      const [projectResult, environmentResult, integrationResult] = await Promise.all([
        getProject(accessToken, projectId),
        getProjectEnvironments(accessToken, projectId),
        getProjectIntegrations(accessToken, projectId),
      ]);

      setProject(projectResult);
      setEnvironments(environmentResult);
      setIntegrations(integrationResult);
    } catch (error: unknown) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [accessToken, projectId]);

  useEffect(() => {
    if (!accessToken || !projectId) {
      return;
    }

    const token = accessToken;
    const currentProjectId = projectId;
    let isActive = true;

    async function loadInitialWorkspace() {
      try {
        const [projectResult, environmentResult, integrationResult] = await Promise.all([
          getProject(token, currentProjectId),
          getProjectEnvironments(token, currentProjectId),
          getProjectIntegrations(token, currentProjectId),
        ]);

        if (isActive) {
          setProject(projectResult);
          setEnvironments(environmentResult);
          setIntegrations(integrationResult);
        }
      } catch (error: unknown) {
        if (isActive) {
          setPageError(getErrorMessage(error));
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadInitialWorkspace();

    return () => {
      isActive = false;
    };
  }, [accessToken, projectId]);

  useEffect(() => {
    if (!accessToken || !projectId) return;

    const callbackParams = new URLSearchParams(window.location.search);
    const githubResult = callbackParams.get("github");

    if (githubResult !== "connected" && githubResult !== "error") return;

    window.history.replaceState({}, "", window.location.pathname);

    if (githubResult === "connected") {
      setIntegrationError(null);
      setIntegrationSuccess("GitHub App installation was verified and connected successfully.");
      void loadWorkspace(true);
    } else {
      setIntegrationSuccess(null);
      setIntegrationError("GitHub App installation was not completed. You can try connecting again.");
    }
  }, [accessToken, projectId, loadWorkspace]);

  function openCreateForm() {
    setEditingEnvironment(null);
    setForm(emptyForm);
    setEnvironmentError(null);
    setSuccessMessage(null);
    setIsFormOpen(true);
  }

  function openEditForm(environment: ProjectEnvironment) {
    setEditingEnvironment(environment);
    setForm({
      name: environment.name,
      environment_type: environment.environment_type,
      description: environment.description ?? "",
      base_url: environment.base_url ?? "",
      is_primary: environment.is_primary,
    });
    setEnvironmentError(null);
    setSuccessMessage(null);
    setIsFormOpen(true);
  }

  function closeForm() {
    if (isSaving) return;

    setIsFormOpen(false);
    setEditingEnvironment(null);
    setForm(emptyForm);
  }

  async function handleEnvironmentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!accessToken || !projectId) return;

    setIsSaving(true);
    setEnvironmentError(null);
    setSuccessMessage(null);

    const payload: EnvironmentCreateInput = {
      name: form.name.trim(),
      environment_type: form.environment_type,
      description: form.description.trim() || null,
      base_url: form.base_url.trim() || null,
      is_primary: form.is_primary,
      is_active: true,
    };

    try {
      if (editingEnvironment) {
        const updatePayload: EnvironmentUpdateInput = {
          name: payload.name,
          environment_type: payload.environment_type,
          description: payload.description,
          base_url: payload.base_url,
          is_primary: payload.is_primary,
        };

        const updated = await updateProjectEnvironment(
          accessToken,
          projectId,
          editingEnvironment.id,
          updatePayload,
        );

        setEnvironments((current) =>
          current.map((item) =>
            item.id === updated.id ? updated : {
              ...item,
              is_primary: updated.is_primary ? false : item.is_primary,
            },
          ),
        );

        setSuccessMessage("Environment updated successfully.");
      } else {
        const created = await createProjectEnvironment(
          accessToken,
          projectId,
          payload,
        );

        setEnvironments((current) => [
          ...current.map((item) => ({
            ...item,
            is_primary: created.is_primary ? false : item.is_primary,
          })),
          created,
        ]);

        setSuccessMessage("Environment created successfully.");
      }

      setIsFormOpen(false);
      setEditingEnvironment(null);
      setForm(emptyForm);

      await loadWorkspace(true);
    } catch (error: unknown) {
      setEnvironmentError(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeactivate(environment: ProjectEnvironment) {
    if (!accessToken || !projectId) return;

    const confirmed = window.confirm(
      `Deactivate "${environment.name}"? This preserves its history but makes it inactive.`,
    );

    if (!confirmed) return;

    setDeactivatingId(environment.id);
    setEnvironmentError(null);
    setSuccessMessage(null);

    try {
      await deactivateProjectEnvironment(
        accessToken,
        projectId,
        environment.id,
      );

      setSuccessMessage(`"${environment.name}" was deactivated.`);
      await loadWorkspace(true);
    } catch (error: unknown) {
      setEnvironmentError(getErrorMessage(error));
    } finally {
      setDeactivatingId(null);
    }
  }

  function openCreateIntegrationForm() {
    setEditingIntegration(null);
    setIntegrationForm(emptyIntegrationForm);
    setIntegrationError(null);
    setIntegrationSuccess(null);
    setIsIntegrationFormOpen(true);
  }

  function openEditIntegrationForm(integration: ProjectIntegration) {
    setEditingIntegration(integration);
    setIntegrationForm({
      name: integration.name,
      integration_type: integration.integration_type,
      environment_id: integration.environment_id ?? "",
      external_reference: integration.external_reference ?? "",
    });
    setIntegrationError(null);
    setIntegrationSuccess(null);
    setIsIntegrationFormOpen(true);
  }

  function closeIntegrationForm() {
    if (isSavingIntegration) return;
    setIsIntegrationFormOpen(false);
    setEditingIntegration(null);
    setIntegrationForm(emptyIntegrationForm);
    setIntegrationError(null);
  }

  async function handleIntegrationSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!accessToken || !projectId) return;

    setIsSavingIntegration(true);
    setIntegrationError(null);
    setIntegrationSuccess(null);

    try {
      if (editingIntegration) {
        const payload: IntegrationUpdateInput = {
          name: integrationForm.name.trim(),
          environment_id: integrationForm.environment_id || null,
          external_reference: integrationForm.external_reference.trim() || null,
        };

        await updateProjectIntegration(
          accessToken,
          projectId,
          editingIntegration.id,
          payload,
        );

        setIntegrationSuccess(`"${integrationForm.name.trim()}" was updated.`);
      } else {
        const payload: IntegrationCreateInput = {
          name: integrationForm.name.trim(),
          integration_type: integrationForm.integration_type,
          environment_id: integrationForm.environment_id || null,
          external_reference: integrationForm.external_reference.trim() || null,
        };

        const created = await createProjectIntegration(
          accessToken,
          projectId,
          payload,
        );

        setIntegrations((current) => [...current, created]);
        setIntegrationSuccess(
          `"${created.name}" was registered. Provider setup is still required to establish a live connection.`,
        );
      }

      setIsIntegrationFormOpen(false);
      setEditingIntegration(null);
      setIntegrationForm(emptyIntegrationForm);
      await loadWorkspace(true);
    } catch (error: unknown) {
      setIntegrationError(getErrorMessage(error));
    } finally {
      setIsSavingIntegration(false);
    }
  }

  async function handleDisconnectIntegration(integration: ProjectIntegration) {
    if (!accessToken || !projectId) return;

    const confirmed = window.confirm(
      `Disconnect "${integration.name}"? Its record will be retained for history and auditing.`,
    );

    if (!confirmed) return;

    setDisconnectingIntegrationId(integration.id);
    setIntegrationError(null);
    setIntegrationSuccess(null);

    try {
      await disconnectProjectIntegration(
        accessToken,
        projectId,
        integration.id,
      );

      await loadWorkspace(true);
      setIntegrationSuccess(`"${integration.name}" was disconnected.`);
    } catch (error: unknown) {
      setIntegrationError(getErrorMessage(error));
    } finally {
      setDisconnectingIntegrationId(null);
    }
  }

  async function handleGitHubInstall(integration: ProjectIntegration) {
    if (!accessToken || !projectId || installingGitHubIntegrationId) return;

    setInstallingGitHubIntegrationId(integration.id);
    setIntegrationError(null);
    setIntegrationSuccess(null);

    try {
      const result = await startProjectGitHubInstallation(
        accessToken,
        projectId,
        integration.id,
      );

      const authorizationUrl = new URL(result.authorization_url);

      if (
        authorizationUrl.protocol !== "https:" ||
        authorizationUrl.hostname !== "github.com" ||
        !authorizationUrl.pathname.startsWith("/apps/") ||
        !authorizationUrl.pathname.endsWith("/installations/new")
      ) {
        throw new Error("The server returned an unexpected GitHub authorization URL.");
      }

      window.location.assign(authorizationUrl.toString());
    } catch (error: unknown) {
      setIntegrationError(getErrorMessage(error));
      setInstallingGitHubIntegrationId(null);
    }
  }

  const activeEnvironmentCount = environments.filter(
    (environment) => environment.is_active,
  ).length;

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
        <div className="flex flex-col items-center gap-3">
          <LoaderCircle size={34} className="animate-spin text-blue-400" />
          <p className="text-sm">Loading project workspace...</p>
        </div>
      </main>
    );
  }

  if (pageError || !project) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-200">
        <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900/70 p-7 text-center">
          <CircleAlert className="mx-auto text-amber-400" size={36} />
          <h1 className="mt-4 text-xl font-semibold">
            Unable to open project
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-400">
            {pageError ?? "The requested project is unavailable."}
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <button
              type="button"
              onClick={() => void loadWorkspace()}
              className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-500"
            >
              Try again
            </button>
            <Link
              href="/dashboard"
              className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-800"
            >
              Dashboard
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#080f1d] text-slate-100">
      <div className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-10">
        {/* Top navigation */}
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
              <FolderKanban size={21} />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-wide text-white">
                SherlskyyCommand
              </p>
              <p className="text-xs text-slate-500">
                Project operations workspace
              </p>
            </div>
          </div>

          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 transition hover:border-slate-500 hover:bg-slate-800"
          >
            <ArrowLeft size={15} />
            Back to dashboard
          </Link>
        </header>

        {/* Breadcrumb */}
        <nav className="mt-6 flex items-center gap-2 text-xs text-slate-500">
          <Link href="/dashboard" className="hover:text-blue-400">
            Dashboard
          </Link>
          <ChevronRight size={13} />
          <span className="text-slate-300">{project.name}</span>
        </nav>

        {/* Project heading */}
        <section className="mt-7 flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="break-words text-2xl font-bold tracking-tight text-white sm:text-3xl">
                {project.name}
              </h1>
              <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-xs font-semibold capitalize text-blue-300">
                {project.status}
              </span>
            </div>

            <p className="mt-2 font-mono text-xs text-slate-500">
              {project.slug}
            </p>

            <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-400">
              {project.description || "No project description has been added."}
            </p>
          </div>

          <button
            type="button"
            onClick={() => void loadWorkspace(true)}
            disabled={isRefreshing}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw
              size={15}
              className={isRefreshing ? "animate-spin" : ""}
            />
            Refresh workspace
          </button>
        </section>

        {/* Project statistics */}
        <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-slate-800 bg-[#0c1728] p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-400">Environments</p>
              <Globe size={19} className="text-blue-400" />
            </div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">
              {environments.length}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Configured environments
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-[#0c1728] p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-400">Active environments</p>
              <CheckCircle2 size={19} className="text-emerald-400" />
            </div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">
              {activeEnvironmentCount}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Currently enabled
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-[#0c1728] p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-400">Project status</p>
              <Activity size={19} className="text-purple-400" />
            </div>
            <p className="mt-3 text-xl font-semibold capitalize">
              {project.status}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Current project state
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-[#0c1728] p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-400">Last updated</p>
              <Server size={19} className="text-amber-400" />
            </div>
            <p className="mt-3 text-sm font-semibold">
              {formatDate(project.updated_at)}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Project record timestamp
            </p>
          </div>
        </section>

        {/* Workspace navigation */}
        <section className="mt-9">
          <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-3">
            <span className="inline-flex items-center gap-2 rounded-lg bg-blue-500/10 px-3 py-2 text-sm font-medium text-blue-300">
              <FolderKanban size={16} />
              Overview
            </span>
            <span className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-500">
              <Code2 size={16} />
              Development
            </span>
            <span className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-500">
              <Activity size={16} />
              Monitoring
            </span>
            <span className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-500">
              <ShieldCheck size={16} />
              Security
            </span>
          </div>
        </section>

        {/* Environment management */}
        <section className="mt-8">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <h2 className="text-lg font-semibold text-white">
                Project environments
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Manage development, staging, production, and custom environments.
              </p>
            </div>

            <button
              type="button"
              onClick={openCreateForm}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
            >
              <Plus size={17} />
              Add environment
            </button>
          </div>

          {successMessage && (
            <div className="mt-5 flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
              <CheckCircle2 size={17} />
              {successMessage}
            </div>
          )}

          {environmentError && (
            <div className="mt-5 flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              <CircleAlert size={17} className="mt-0.5 shrink-0" />
              <span>{environmentError}</span>
            </div>
          )}

          {isFormOpen && (
            <form
              onSubmit={handleEnvironmentSubmit}
              className="mt-6 rounded-2xl border border-blue-500/20 bg-[#0c1728] p-5 sm:p-6"
            >
              <div className="mb-5 flex items-center justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-white">
                    {editingEnvironment ? "Edit environment" : "New environment"}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500">
                    Environment details are saved to the project database.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={closeForm}
                  disabled={isSaving}
                  aria-label="Close environment form"
                  className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="grid gap-5 md:grid-cols-2">
                <label className="block">
                  <span className="mb-2 block text-sm text-slate-300">
                    Environment name *
                  </span>
                  <input
                    required
                    minLength={2}
                    maxLength={100}
                    value={form.name}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        name: event.target.value,
                      }))
                    }
                    placeholder="e.g. Production East"
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm text-slate-300">
                    Environment type *
                  </span>
                  <select
                    value={form.environment_type}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        environment_type: event.target.value as ProjectEnvironment["environment_type"],
                      }))
                    }
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-white outline-none focus:border-blue-500"
                  >
                    {environmentTypes.map((type) => (
                      <option key={type} value={type}>
                        {type.charAt(0).toUpperCase() + type.slice(1)}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block md:col-span-2">
                  <span className="mb-2 block text-sm text-slate-300">
                    Base URL
                  </span>
                  <input
                    type="url"
                    maxLength={500}
                    value={form.base_url}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        base_url: event.target.value,
                      }))
                    }
                    placeholder="https://example.com"
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                  />
                  <span className="mt-1 block text-xs text-slate-500">
                    Optional. HTTP is also accepted for local development.
                  </span>
                </label>

                <label className="block md:col-span-2">
                  <span className="mb-2 block text-sm text-slate-300">
                    Description
                  </span>
                  <textarea
                    rows={3}
                    maxLength={2000}
                    value={form.description}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        description: event.target.value,
                      }))
                    }
                    placeholder="Describe what this environment is used for..."
                    className="w-full resize-y rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                  />
                </label>

                <label className="flex items-center gap-3 text-sm text-slate-300 md:col-span-2">
                  <input
                    type="checkbox"
                    checked={form.is_primary}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        is_primary: event.target.checked,
                      }))
                    }
                    className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-blue-500 focus:ring-blue-500"
                  />
                  Set as the primary environment
                </label>
              </div>

              <div className="mt-6 flex flex-wrap justify-end gap-3 border-t border-slate-800 pt-5">
                <button
                  type="button"
                  onClick={closeForm}
                  disabled={isSaving}
                  className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isSaving && <LoaderCircle size={16} className="animate-spin" />}
                  {isSaving
                    ? "Saving..."
                    : editingEnvironment
                      ? "Save changes"
                      : "Create environment"}
                </button>
              </div>
            </form>
          )}

          {environments.length === 0 ? (
            <div className="mt-6 rounded-2xl border border-dashed border-slate-700 bg-[#0c1728]/60 px-6 py-14 text-center">
              <Globe className="mx-auto text-slate-600" size={36} />
              <h3 className="mt-4 font-semibold text-slate-200">
                No environments configured
              </h3>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
                Add your first environment to start organizing this project&apos;s
                development, staging, and production deployments.
              </p>
              <button
                type="button"
                onClick={openCreateForm}
                className="mt-5 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500"
              >
                <Plus size={16} />
                Create first environment
              </button>
            </div>
          ) : (
            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              {environments.map((environment) => (
                <article
                  key={environment.id}
                  className="rounded-2xl border border-slate-800 bg-[#0c1728] p-5 transition hover:border-slate-700"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-800 text-blue-400">
                        <Server size={19} />
                      </div>
                      <div className="min-w-0">
                        <h3 className="truncate font-semibold text-white">
                          {environment.name}
                        </h3>
                        <p className="mt-1 text-xs text-slate-500">
                          Created {formatDate(environment.created_at)}
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <span
                        className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold ${typeStyles[environment.environment_type]}`}
                      >
                        {environment.environment_type.toUpperCase()}
                      </span>
                      {environment.is_primary && (
                        <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2.5 py-1 text-[10px] font-semibold text-blue-300">
                          PRIMARY
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="mt-4 min-h-5 text-sm text-slate-400">
                    {environment.description || "No description provided."}
                  </p>

                  {environment.base_url && (
                    <a
                      href={environment.base_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-4 inline-flex max-w-full items-center gap-2 break-all text-xs text-blue-400 hover:text-blue-300"
                    >
                      <Globe size={14} className="shrink-0" />
                      {environment.base_url}
                      <ExternalLink size={12} className="shrink-0" />
                    </a>
                  )}

                  <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-4">
                    <span
                      className={`inline-flex items-center gap-2 text-xs ${
                        environment.is_active
                          ? "text-emerald-400"
                          : "text-slate-500"
                      }`}
                    >
                      <span
                        className={`h-2 w-2 rounded-full ${
                          environment.is_active
                            ? "bg-emerald-400"
                            : "bg-slate-600"
                        }`}
                      />
                      {environment.is_active ? "Active" : "Inactive"}
                    </span>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => openEditForm(environment)}
                        disabled={!environment.is_active || isSaving}
                        className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-medium text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        Edit
                      </button>

                      {environment.is_active && (
                        <button
                          type="button"
                          onClick={() => void handleDeactivate(environment)}
                          disabled={deactivatingId === environment.id}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-red-500/20 px-3 py-2 text-xs font-medium text-red-300 transition hover:bg-red-500/10 disabled:opacity-50"
                        >
                          {deactivatingId === environment.id ? (
                            <LoaderCircle size={13} className="animate-spin" />
                          ) : (
                            <Trash2 size={13} />
                          )}
                          Deactivate
                        </button>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {/* Project integrations */}
        <section className="mt-10">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <h2 className="text-lg font-semibold text-white">
                Project integrations
              </h2>
              <p className="mt-1 max-w-2xl text-sm text-slate-500">
                Register the external services that power this project.
                Live data appears after each provider is connected.
              </p>
            </div>

            <button
              type="button"
              onClick={openCreateIntegrationForm}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
            >
              <Plus size={17} />
              Add integration
            </button>
          </div>

          {integrationSuccess && (
            <div className="mt-5 flex items-start gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
              <CheckCircle2 size={17} className="mt-0.5 shrink-0" />
              <span>{integrationSuccess}</span>
            </div>
          )}

          {integrationError && (
            <div className="mt-5 flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              <CircleAlert size={17} className="mt-0.5 shrink-0" />
              <span>{integrationError}</span>
            </div>
          )}

          {isIntegrationFormOpen && (
            <form
              onSubmit={handleIntegrationSubmit}
              className="mt-6 rounded-2xl border border-blue-500/20 bg-[#0c1728] p-5 sm:p-6"
            >
              <div className="mb-5 flex items-center justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-white">
                    {editingIntegration ? "Edit integration" : "Register integration"}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500">
                    Credentials and secrets are configured separately through secure provider setup.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={closeIntegrationForm}
                  disabled={isSavingIntegration}
                  aria-label="Close integration form"
                  className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-50"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="grid gap-5 md:grid-cols-2">
                <label className="block">
                  <span className="mb-2 block text-sm text-slate-300">
                    Integration name *
                  </span>
                  <input
                    required
                    minLength={2}
                    maxLength={150}
                    value={integrationForm.name}
                    onChange={(event) =>
                      setIntegrationForm((current) => ({
                        ...current,
                        name: event.target.value,
                      }))
                    }
                    placeholder="e.g. Main GitHub repository"
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm text-slate-300">
                    Provider type *
                  </span>
                  <select
                    value={integrationForm.integration_type}
                    disabled={Boolean(editingIntegration)}
                    onChange={(event) =>
                      setIntegrationForm((current) => ({
                        ...current,
                        integration_type: event.target.value as ProjectIntegration["integration_type"],
                      }))
                    }
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-white outline-none focus:border-blue-500 disabled:opacity-60"
                  >
                    <option value="github">GitHub</option>
                    <option value="server_agent">Server agent</option>
                    <option value="application">Application</option>
                    <option value="database">Database</option>
                  </select>
                  {editingIntegration && (
                    <span className="mt-1 block text-xs text-slate-500">
                      Provider type cannot be changed after registration.
                    </span>
                  )}
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm text-slate-300">
                    Environment
                  </span>
                  <select
                    value={integrationForm.environment_id}
                    onChange={(event) =>
                      setIntegrationForm((current) => ({
                        ...current,
                        environment_id: event.target.value,
                      }))
                    }
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-white outline-none focus:border-blue-500"
                  >
                    <option value="">No environment assigned</option>
                    {environments
                      .filter((environment) => environment.is_active)
                      .map((environment) => (
                        <option key={environment.id} value={environment.id}>
                          {environment.name}
                        </option>
                      ))}
                  </select>
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm text-slate-300">
                    External reference
                  </span>
                  <input
                    maxLength={500}
                    value={integrationForm.external_reference}
                    onChange={(event) =>
                      setIntegrationForm((current) => ({
                        ...current,
                        external_reference: event.target.value,
                      }))
                    }
                    placeholder="Repository URL, host ID, or service reference"
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                  />
                </label>
              </div>

              <div className="mt-6 flex flex-wrap justify-end gap-3">
                <button
                  type="button"
                  onClick={closeIntegrationForm}
                  disabled={isSavingIntegration}
                  className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-slate-800 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingIntegration}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isSavingIntegration && (
                    <LoaderCircle size={15} className="animate-spin" />
                  )}
                  {isSavingIntegration
                    ? "Saving..."
                    : editingIntegration
                      ? "Save changes"
                      : "Register integration"}
                </button>
              </div>
            </form>
          )}

          {integrations.length === 0 ? (
            <div className="mt-6 rounded-2xl border border-dashed border-slate-700 bg-[#0c1728]/50 px-5 py-10 text-center">
              <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-slate-800 text-slate-400">
                <Code2 size={21} />
              </div>
              <h3 className="mt-4 font-semibold text-white">
                No integrations registered
              </h3>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
                Add GitHub, server, application, or database integrations to
                begin connecting this project to its external systems.
              </p>
            </div>
          ) : (
            <div className="mt-6 grid gap-4 xl:grid-cols-2">
              {integrations.map((integration) => {
                const statusLabel: Record<ProjectIntegration["status"], string> = {
                  pending: "Awaiting setup",
                  connected: "Connected",
                  degraded: "Degraded",
                  disconnected: "Disconnected",
                  error: "Error",
                };

                const statusClass: Record<ProjectIntegration["status"], string> = {
                  pending: "border-amber-500/20 bg-amber-500/10 text-amber-300",
                  connected: "border-emerald-500/20 bg-emerald-500/10 text-emerald-300",
                  degraded: "border-orange-500/20 bg-orange-500/10 text-orange-300",
                  disconnected: "border-slate-600 bg-slate-800/70 text-slate-400",
                  error: "border-red-500/20 bg-red-500/10 text-red-300",
                };

                const typeLabel: Record<ProjectIntegration["integration_type"], string> = {
                  github: "GitHub",
                  server_agent: "Server agent",
                  application: "Application",
                  database: "Database",
                };

                const environmentName = environments.find(
                  (environment) => environment.id === integration.environment_id,
                )?.name ?? "No environment assigned";

                return (
                  <article
                    key={integration.id}
                    className="rounded-2xl border border-slate-800 bg-[#0c1728] p-5 transition hover:border-slate-700"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="flex min-w-0 items-start gap-3">
                        <div className="rounded-xl bg-blue-500/10 p-2.5 text-blue-400">
                          {integration.integration_type === "github" ? (
                            <Code2 size={19} />
                          ) : integration.integration_type === "server_agent" ? (
                            <Server size={19} />
                          ) : integration.integration_type === "database" ? (
                            <Activity size={19} />
                          ) : (
                            <Globe size={19} />
                          )}
                        </div>
                        <div className="min-w-0">
                          <h3 className="break-words font-semibold text-white">
                            {integration.name}
                          </h3>
                          <p className="mt-1 text-xs text-slate-500">
                            {typeLabel[integration.integration_type]}
                          </p>
                        </div>
                      </div>

                      <span
                        className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-medium ${statusClass[integration.status]}`}
                      >
                        {statusLabel[integration.status]}
                      </span>
                    </div>

                    <dl className="mt-5 grid gap-3 border-t border-slate-800 pt-4 sm:grid-cols-2">
                      <div>
                        <dt className="text-xs text-slate-500">Environment</dt>
                        <dd className="mt-1 break-words text-sm text-slate-300">
                          {environmentName}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-slate-500">Last activity reported</dt>
                        <dd className="mt-1 text-sm text-slate-300">
                          {integration.last_seen_at
                            ? formatDate(integration.last_seen_at)
                            : "Not reported yet"}
                        </dd>
                      </div>
                      {integration.external_reference && (
                        <div className="sm:col-span-2">
                          <dt className="text-xs text-slate-500">External reference</dt>
                          <dd className="mt-1 break-all text-sm text-slate-400">
                            {integration.external_reference}
                          </dd>
                        </div>
                      )}
                    </dl>

                    <div className="mt-5 flex flex-wrap justify-end gap-2 border-t border-slate-800 pt-4">
                      {integration.integration_type === "github" && integration.status !== "connected" && (
                        <button
                          type="button"
                          onClick={() => void handleGitHubInstall(integration)}
                          disabled={Boolean(installingGitHubIntegrationId) || isSavingIntegration || Boolean(disconnectingIntegrationId)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-xs font-semibold text-blue-300 transition hover:bg-blue-500/20 disabled:opacity-50"
                        >
                          {installingGitHubIntegrationId === integration.id ? (
                            <LoaderCircle size={13} className="animate-spin" />
                          ) : (
                            <ExternalLink size={13} />
                          )}
                          {installingGitHubIntegrationId === integration.id
                            ? "Redirecting to GitHub..."
                            : integration.status === "disconnected"
                              ? "Reconnect GitHub App"
                              : "Install GitHub App"}
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => openEditIntegrationForm(integration)}
                        disabled={Boolean(disconnectingIntegrationId) || isSavingIntegration}
                        className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-medium text-slate-300 transition hover:bg-slate-800 disabled:opacity-40"
                      >
                        Edit
                      </button>

                      {integration.status !== "disconnected" && (
                        <button
                          type="button"
                          onClick={() => void handleDisconnectIntegration(integration)}
                          disabled={disconnectingIntegrationId === integration.id}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-red-500/20 px-3 py-2 text-xs font-medium text-red-300 transition hover:bg-red-500/10 disabled:opacity-50"
                        >
                          {disconnectingIntegrationId === integration.id ? (
                            <LoaderCircle size={13} className="animate-spin" />
                          ) : (
                            <X size={13} />
                          )}
                          Disconnect
                        </button>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {/* Honest integration status */}
        <section className="mt-10 rounded-2xl border border-slate-800 bg-[#0c1728]/70 p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <div className="rounded-xl bg-blue-500/10 p-2.5 text-blue-400">
              <Activity size={19} />
            </div>
            <div>
              <h2 className="font-semibold text-white">
                Operational monitoring
              </h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                Live application health, GitHub activity, infrastructure
                metrics, database events, scheduling, audit logs, and
                notifications will appear here as their integrations are
                connected. No monitoring status is reported until a real
                integration supplies it.
              </p>
              <p className="mt-3 text-xs text-slate-500">
                Project created: {formatDate(project.created_at)}
              </p>
            </div>
          </div>
        </section>

        <footer className="mt-10 border-t border-slate-800 py-5 text-xs text-slate-600">
          SherlskyyCommand · Project workspace
        </footer>
      </div>
    </main>
  );
}

// ---------------------------------------------------------
// Protected page entry point
// ---------------------------------------------------------

export default function ProjectWorkspacePage() {
  return (
    <ProtectedRoute>
      <ProjectWorkspaceContent />
    </ProtectedRoute>
  );
}
