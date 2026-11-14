
export type ProjectStatus = 'Active' | 'Planning' | 'Completed';

export interface DashboardProject {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  progress: number;
  updatedAt: string;
}

export interface DashboardStat {
  id: string;
  label: string;
  value: number;
  description: string;
  icon: 'folder' | 'activity' | 'check' | 'clock';
}

export const dashboardStats: DashboardStat[] = [
  {
    id: 'projects',
    label: 'Total projects',
    value: 5,
    description: 'Across your workspace',
    icon: 'folder',
  },
  {
    id: 'active',
    label: 'Active projects',
    value: 3,
    description: 'Currently in progress',
    icon: 'activity',
  },
  {
    id: 'completed',
    label: 'Completed',
    value: 1,
    description: 'Successfully completed',
    icon: 'check',
  },
  {
    id: 'tasks',
    label: 'Pending tasks',
    value: 12,
    description: 'Awaiting completion',
    icon: 'clock',
  },
];

export const recentProjects: DashboardProject[] = [
  {
    id: 'agricore',
    name: 'AgriCore',
    description: 'Farm management platform',
    status: 'Active',
    progress: 75,
    updatedAt: 'Recently updated',
  },
  {
    id: 'sherlskyy-ai',
    name: 'Sherlskyy AI',
    description: 'Personal offline AI assistant',
    status: 'Active',
    progress: 55,
    updatedAt: 'Recently updated',
  },
  {
    id: 'portfolio',
    name: 'Developer Portfolio',
    description: 'Personal developer portfolio',
    status: 'Completed',
    progress: 100,
    updatedAt: 'Recently updated',
  },
  {
    id: 'jerseyshop',
    name: 'JerseyShop',
    description: 'Online jersey shopping platform',
    status: 'Planning',
    progress: 20,
    updatedAt: 'Recently updated',
  },
];
