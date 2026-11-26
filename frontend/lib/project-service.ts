
import { apiClient } from "./api-client";

// ---------------------------------------------------------
// Project types
// ---------------------------------------------------------

export type ProjectStatus =
  | "planned"
  | "active"
  | "paused"
  | "completed"
  | "archived";

export interface Project {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  status: ProjectStatus;
  created_by_id: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreateInput {
  name: string;
  description: string | null;
}

// ---------------------------------------------------------
// Project API service
// ---------------------------------------------------------

/**
 * Retrieve projects created by or shared with the current user.
 */
export async function getProjects(
  accessToken: string,
): Promise<Project[]> {
  const response = await apiClient.get<Project[]>("/projects", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  return response.data;
}

/**
 * Create a project for the authenticated user.
 *
 * The backend determines the creator, status, and slug.
 */
export async function createProject(
  accessToken: string,
  payload: ProjectCreateInput,
): Promise<Project> {
  const response = await apiClient.post<Project>("/projects", payload, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  return response.data;
}

// ---------------------------------------------------------
// Project detail and environment types
// ---------------------------------------------------------

export interface ProjectEnvironment {
  id: string;
  project_id: string;
  name: string;
  environment_type: "development" | "staging" | "production" | "custom";
  description: string | null;
  base_url: string | null;
  is_primary: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EnvironmentCreateInput {
  name: string;
  environment_type: ProjectEnvironment["environment_type"];
  description?: string | null;
  base_url?: string | null;
  is_primary?: boolean;
  is_active?: boolean;
}

export interface EnvironmentUpdateInput {
  name?: string;
  environment_type?: ProjectEnvironment["environment_type"];
  description?: string | null;
  base_url?: string | null;
  is_primary?: boolean;
  is_active?: boolean;
}

// ---------------------------------------------------------
// Individual project API
// ---------------------------------------------------------

export async function getProject(
  accessToken: string,
  projectId: string,
): Promise<Project> {
  const response = await apiClient.get<Project>(
    `/projects/${encodeURIComponent(projectId)}`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );

  return response.data;
}

// ---------------------------------------------------------
// Project environment API
// ---------------------------------------------------------

export async function getProjectEnvironments(
  accessToken: string,
  projectId: string,
): Promise<ProjectEnvironment[]> {
  const response = await apiClient.get<ProjectEnvironment[]>(
    `/projects/${encodeURIComponent(projectId)}/environments`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );

  return response.data;
}

export async function createProjectEnvironment(
  accessToken: string,
  projectId: string,
  payload: EnvironmentCreateInput,
): Promise<ProjectEnvironment> {
  const response = await apiClient.post<ProjectEnvironment>(
    `/projects/${encodeURIComponent(projectId)}/environments`,
    payload,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );

  return response.data;
}

export async function updateProjectEnvironment(
  accessToken: string,
  projectId: string,
  environmentId: string,
  payload: EnvironmentUpdateInput,
): Promise<ProjectEnvironment> {
  const response = await apiClient.patch<ProjectEnvironment>(
    `/projects/${encodeURIComponent(projectId)}/environments/${encodeURIComponent(environmentId)}`,
    payload,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );

  return response.data;
}

export async function deactivateProjectEnvironment(
  accessToken: string,
  projectId: string,
  environmentId: string,
): Promise<void> {
  await apiClient.delete(
    `/projects/${encodeURIComponent(projectId)}/environments/${encodeURIComponent(environmentId)}`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );
}

// ---------------------------------------------------------

// ---------------------------------------------------------
// Project integration types
// ---------------------------------------------------------

export type IntegrationType =
  | "github"
  | "server_agent"
  | "application"
  | "database";

export type IntegrationStatus =
  | "pending"
  | "connected"
  | "degraded"
  | "disconnected"
  | "error";

export interface ProjectIntegration {
  id: string;
  project_id: string;
  environment_id: string | null;
  integration_type: IntegrationType;
  name: string;
  external_reference: string | null;
  status: IntegrationStatus;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface IntegrationCreateInput {
  name: string;
  integration_type: IntegrationType;
  environment_id?: string | null;
  external_reference?: string | null;
}

export interface IntegrationUpdateInput {
  name?: string;
  environment_id?: string | null;
  external_reference?: string | null;
}

// ---------------------------------------------------------
// Project integration API
// ---------------------------------------------------------

export async function getProjectIntegrations(
  accessToken: string,
  projectId: string,
): Promise<ProjectIntegration[]> {
  const response = await apiClient.get<ProjectIntegration[]>(
    `/projects/${encodeURIComponent(projectId)}/integrations`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  return response.data;
}

export async function createProjectIntegration(
  accessToken: string,
  projectId: string,
  payload: IntegrationCreateInput,
): Promise<ProjectIntegration> {
  const response = await apiClient.post<ProjectIntegration>(
    `/projects/${encodeURIComponent(projectId)}/integrations`,
    payload,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  return response.data;
}

export interface GitHubInstallationResponse {
  authorization_url: string;
  expires_in: number;
}

export async function startProjectGitHubInstallation(
  accessToken: string,
  projectId: string,
  integrationId: string,
): Promise<GitHubInstallationResponse> {
  const response = await apiClient.post<GitHubInstallationResponse>(
    `/projects/${encodeURIComponent(projectId)}/integrations/${encodeURIComponent(integrationId)}/github/install`,
    {},
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );

  return response.data;
}

export async function updateProjectIntegration(
  accessToken: string,
  projectId: string,
  integrationId: string,
  payload: IntegrationUpdateInput,
): Promise<ProjectIntegration> {
  const response = await apiClient.patch<ProjectIntegration>(
    `/projects/${encodeURIComponent(projectId)}/integrations/${encodeURIComponent(integrationId)}`,
    payload,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  return response.data;
}

export async function disconnectProjectIntegration(
  accessToken: string,
  projectId: string,
  integrationId: string,
): Promise<void> {
  await apiClient.delete(
    `/projects/${encodeURIComponent(projectId)}/integrations/${encodeURIComponent(integrationId)}`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
}
