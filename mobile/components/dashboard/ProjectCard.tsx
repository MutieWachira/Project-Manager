
import { StyleSheet, View } from 'react-native';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import { Text } from '@/components/Themed';

import type { DashboardProject } from '@/data/dashboard/dashboard-data';

interface ProjectCardProps {
  project: DashboardProject;
  compact?: boolean;
}

export default function ProjectCard({
  project,
  compact = false,
}: ProjectCardProps) {
  const colorScheme = useColorScheme();
  const theme = Colors[colorScheme];

  const statusColor = {
    Active: '#2563EB',
    Planning: '#D97706',
    Completed: '#16A34A',
  }[project.status];

  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: theme.surface,
          borderColor: theme.border,
          padding: compact ? 12 : 16,
          gap: compact ? 10 : 14,
        },
      ]}
    >
      <View style={styles.topRow}>
        <View style={styles.projectInfo}>
          <Text style={styles.name}>{project.name}</Text>

          <Text style={[styles.description, { color: theme.muted }]}>
            {project.description}
          </Text>
        </View>

        <View
          style={[
            styles.status,
            { backgroundColor: `${statusColor}18` },
          ]}
        >
          <Text style={[styles.statusText, { color: statusColor }]}>
            {project.status}
          </Text>
        </View>
      </View>

      <View style={styles.progressHeader}>
        <Text style={[styles.progressLabel, { color: theme.muted }]}>
          Progress
        </Text>

        <Text style={styles.progressValue}>
          {project.progress}%
        </Text>
      </View>

      <View
        style={[
          styles.progressTrack,
          { backgroundColor: theme.border },
        ]}
      >
        <View
          style={[
            styles.progressFill,
            {
              width: `${project.progress}%`,
              backgroundColor: statusColor,
            },
          ]}
        />
      </View>

      <Text style={[styles.updatedAt, { color: theme.muted }]}>
        {project.updatedAt}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 16,
    borderWidth: 1,
    borderRadius: 16,
    gap: 14,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 10,
  },
  projectInfo: {
    flex: 1,
    gap: 5,
  },
  name: {
    fontSize: 15,
    fontWeight: '700',
  },
  description: {
    fontSize: 12,
  },
  status: {
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: 20,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '700',
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  progressLabel: {
    fontSize: 12,
  },
  progressValue: {
    fontSize: 12,
    fontWeight: '700',
  },
  progressTrack: {
    height: 7,
    borderRadius: 10,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 10,
  },
  updatedAt: {
    fontSize: 11,
  },
});
