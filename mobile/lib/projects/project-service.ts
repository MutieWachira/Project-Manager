import { apiRequest } from '@/lib/api/api-client';

// ---------------------------------------------------------
// Project types
// ---------------------------------------------------------

export type ProjectStatus =
  | 'planned'
  | 'active'
  | 'paused'
  | 'completed'
  | 'archived';

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
// Retrieve accessible projects
// ---------------------------------------------------------

/**
 * Retrieve projects created by or shared with the authenticated user.
 */
export async function getProjects(
  accessToken: string,
): Promise<Project[]> {
  if (!accessToken.trim()) {
    throw new Error('An access token is required to retrieve projects.');
  }

  return apiRequest<Project[]>('/projects', {
    method: 'GET',
    accessToken,
  });
}

// ---------------------------------------------------------
// Create a project
// ---------------------------------------------------------

/**
 * Create a project for the authenticated user.
 *
 * The backend determines the project ID, slug, creator,
 * initial status, and owner membership.
 */
export async function createProject(
  accessToken: string,
  payload: ProjectCreateInput,
): Promise<Project> {
  if (!accessToken.trim()) {
    throw new Error('An access token is required to create a project.');
  }

  const name = payload.name.trim();
  const description = payload.description?.trim() || null;

  if (name.length < 2 || name.length > 150) {
    throw new Error('Project name must contain between 2 and 150 characters.');
  }

  if (description !== null && description.length > 2000) {
    throw new Error('Project description cannot exceed 2,000 characters.');
  }

  return apiRequest<Project>('/projects', {
    method: 'POST',
    accessToken,
    body: {
      name,
      description,
    },
  });
}
