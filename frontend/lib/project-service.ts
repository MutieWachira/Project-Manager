
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
