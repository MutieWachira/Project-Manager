import { useCallback, useEffect, useRef, useState } from 'react';

import { useAuth } from '@/components/providers/auth-provider';
import {
  createProject as createProjectRequest,
  getProjects,
  type Project,
  type ProjectCreateInput,
} from '@/lib/projects/project-service';
import { getApiErrorMessage } from '@/lib/api/api-errors';

interface UseProjectsResult {
  projects: Project[];
  isLoading: boolean;
  isCreating: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  create: (payload: ProjectCreateInput) => Promise<Project>;
}

export function useProjects(): UseProjectsResult {
  const { accessToken } = useAuth();

  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestId = useRef(0);

  const refresh = useCallback(async () => {
    const currentRequestId = ++requestId.current;

    if (!accessToken) {
      setProjects([]);
      setError(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await getProjects(accessToken);

      if (requestId.current === currentRequestId) {
        setProjects(result);
      }
    } catch (err) {
      if (requestId.current === currentRequestId) {
        setError(
          getApiErrorMessage(
            err,
            'Unable to load projects. Please try again.',
          ),
        );
      }
    } finally {
      if (requestId.current === currentRequestId) {
        setIsLoading(false);
      }
    }
  }, [accessToken]);

  const create = useCallback(
    async (payload: ProjectCreateInput): Promise<Project> => {
      if (!accessToken) {
        throw new Error('Your session has expired. Please sign in again.');
      }

      setIsCreating(true);

      try {
        const createdProject = await createProjectRequest(
          accessToken,
          payload,
        );

        // Prevent an older in-flight fetch from overwriting this update.
        requestId.current += 1;
        setIsLoading(false);

        setProjects((currentProjects) => [
          createdProject,
          ...currentProjects.filter(
            (project) => project.id !== createdProject.id,
          ),
        ]);

        setError(null);

        return createdProject;
      } finally {
        setIsCreating(false);
      }
    },
    [accessToken],
  );

  useEffect(() => {
    void refresh();

    return () => {
      requestId.current += 1;
    };
  }, [refresh]);

  return {
    projects,
    isLoading,
    isCreating,
    error,
    refresh,
    create,
  };
}
