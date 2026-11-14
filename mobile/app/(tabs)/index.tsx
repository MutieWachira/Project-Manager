
import { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
  useWindowDimensions,
} from 'react-native';

import { SymbolView } from 'expo-symbols';
import Constants from 'expo-constants';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import { Text } from '@/components/Themed';
import { useAuth } from '@/components/providers/auth-provider';
import { getApiWebSocketUrl } from '@/lib/api/api-client';
import { useProjects } from '@/hooks/use-projects';

import StatCard from '@/components/dashboard/StatCard';
import ProjectCard from '@/components/dashboard/ProjectCard';
import WhatsNew from '@/components/dashboard/WhatsNew';

import type {
  DashboardProject,
  DashboardStat,
} from '@/data/dashboard/dashboard-data';

type DatabaseStatus = 'checking' | 'online' | 'offline';

function getDatabaseStatus(message: unknown): DatabaseStatus | null {
  if (typeof message !== 'string') {
    return null;
  }

  try {
    const data: unknown = JSON.parse(message);
    if (
      typeof data === 'object' &&
      data !== null &&
      'database' in data &&
      (data.database === 'online' || data.database === 'offline')
    ) {
      return data.database;
    }
  } catch (error) {
    console.error('Could not parse database status update.', error);
  }

  return null;
}

export default function DashboardScreen() {
  const colorScheme = useColorScheme();
  const theme = Colors[colorScheme];
  const appVersion = Constants.expoConfig?.version ?? 'Unknown';
  const { width, height, fontScale } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const { logout, user } = useAuth();
  const { projects, isLoading: isLoadingProjects, error: projectsError, refresh } = useProjects();
  const compactLayout = width < 380 || fontScale > 1.15;
  const compactHeight = height < 720;
  const compactSpacing = compactLayout || compactHeight;
  const [databaseStatus, setDatabaseStatus] =
    useState<DatabaseStatus>('checking');
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const dashboardStats = useMemo<DashboardStat[]>(() => {
    const active = projects.filter((project) => project.status === 'active').length;
    const planned = projects.filter((project) => project.status === 'planned').length;
    const completed = projects.filter((project) => project.status === 'completed').length;

    return [
      { id: 'projects', label: 'Total projects', value: projects.length, description: 'Across your workspace', icon: 'folder' },
      { id: 'active', label: 'Active projects', value: active, description: 'Currently in progress', icon: 'activity' },
      { id: 'completed', label: 'Completed', value: completed, description: 'Successfully delivered', icon: 'check' },
      { id: 'planned', label: 'Planned', value: planned, description: 'Ready to begin', icon: 'clock' },
    ];
  }, [projects]);

  const recentProjects = useMemo<DashboardProject[]>(() => projects.slice(0, 4).map((project) => ({
    id: project.id,
    name: project.name,
    description: project.description || 'No description provided.',
    status: project.status === 'completed' ? 'Completed' : project.status === 'planned' ? 'Planning' : 'Active',
    progress: project.status === 'completed' ? 100 : project.status === 'active' ? 60 : 20,
    updatedAt: 'Recently updated',
  })), [projects]);

  async function handleLogout() {
    setIsLoggingOut(true);

    try {
      await logout();
    } catch (error) {
      console.error('Could not complete the logout request.', error);
      Alert.alert(
        'Logged out',
        'Your device session was cleared, but the server could not confirm logout.',
      );
    } finally {
      setIsLoggingOut(false);
    }
  }

  useEffect(() => {
    let active = true;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let reconnectDelay = 1000;
    let socket: WebSocket | undefined;

    function connect() {
      if (!active) return;

      setDatabaseStatus('checking');
      socket = new WebSocket(
        getApiWebSocketUrl('/ws/database-status'),
      );

      socket.onopen = () => {
        reconnectDelay = 1000;
      };

      socket.onmessage = (event) => {
        const status = getDatabaseStatus(event.data);
        if (status) {
          setDatabaseStatus(status);
        } else {
          console.error('Received an invalid database status update.');
        }
      };

      socket.onerror = () => {
        socket?.close();
      };

      socket.onclose = () => {
        if (!active) return;

        setDatabaseStatus('offline');
        reconnectTimer = setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 30_000);
      };
    }

    connect();

    return () => {
      active = false;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      socket?.close();
    };
  }, []);

  return (
    <ScrollView
      style={{ backgroundColor: theme.background }}
      contentContainerStyle={[
        styles.container,
        {
          gap: compactSpacing ? 18 : 28,
          maxWidth: width > 760 ? 760 : undefined,
          paddingHorizontal: Math.max(16, Math.min(24, width * 0.05)),
          paddingTop: insets.top + (compactHeight ? 14 : 20),
          paddingBottom: compactHeight ? 24 : 36,
        },
      ]}
      showsVerticalScrollIndicator={false}
    >
      <View style={styles.welcomeSection}>
        <View style={styles.welcomeText}>
          <Text style={[styles.greeting, { color: theme.muted }]}>
            YOUR WORKSPACE
          </Text>

          <Text style={styles.heading}>
            Welcome back!
          </Text>

          <Text style={[styles.subtitle, { color: theme.muted }]}>
            Your work, priorities, and progress in one place.
          </Text>
        </View>

        <View style={styles.headerActions}>
          <View style={styles.avatarContainer}>
            <View
              style={[
                styles.avatar,
                { backgroundColor: theme.tint },
              ]}
            >
              <Text style={styles.avatarText}>S</Text>
            </View>
            <View
              accessible
              accessibilityRole="image"
              accessibilityLabel={
                databaseStatus === 'checking'
                  ? 'Checking database status'
                  : `Database ${databaseStatus}`
              }
              style={[
                styles.databaseStatusDot,
                {
                  backgroundColor:
                    databaseStatus === 'online'
                      ? '#16A34A'
                      : databaseStatus === 'offline'
                        ? '#DC2626'
                        : theme.muted,
                  borderColor: theme.background,
                },
              ]}
            />
          </View>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Log out"
            accessibilityState={{ disabled: isLoggingOut }}
            disabled={isLoggingOut}
            onPress={() => void handleLogout()}
            style={({ pressed }) => [
              styles.logoutButton,
              {
                backgroundColor: theme.surface,
                borderColor: theme.border,
                opacity: isLoggingOut ? 0.6 : pressed ? 0.7 : 1,
              },
            ]}
          >
            {isLoggingOut ? (
              <ActivityIndicator color={theme.tint} size="small" />
            ) : (
              <SymbolView
                name={{
                  ios: 'rectangle.portrait.and.arrow.right',
                  android: 'logout',
                  web: 'logout',
                }}
                tintColor={theme.tint}
                size={20}
              />
            )}
          </Pressable>
        </View>
      </View>

      <View style={[styles.commandCard, { backgroundColor: theme.tint }]}>
        <View style={styles.commandCopy}>
          <Text style={styles.commandEyebrow}>COMMAND CENTER</Text>
          <Text style={styles.commandTitle}>Keep your projects moving forward.</Text>
          <Text style={styles.commandText}>Review what matters most and stay aligned with your workspace.</Text>
        </View>
        <View style={styles.commandIcon}>
          <SymbolView
            name={{ ios: 'sparkles', android: 'auto_awesome', web: 'auto_awesome' }}
            tintColor="#FFFFFF"
            size={26}
          />
        </View>
      </View>

      <WhatsNew userId={user?.id ?? 'anonymous'} version={appVersion} />

      <View style={[styles.section, compactSpacing && styles.compactSection]}>
        <View style={styles.sectionHeader}>
          <View>
            <Text style={styles.sectionTitle}>Workspace overview</Text>
            <Text style={[styles.sectionSubtitle, { color: theme.muted }]}>A live snapshot of your portfolio</Text>
          </View>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Refresh dashboard"
            onPress={() => void refresh()}
            style={({ pressed }) => [styles.refreshButton, { backgroundColor: theme.surface, borderColor: theme.border, opacity: pressed ? 0.7 : 1 }]}
          >
            {isLoadingProjects ? <ActivityIndicator color={theme.tint} size="small" /> : <SymbolView name={{ ios: 'arrow.clockwise', android: 'refresh', web: 'refresh' }} tintColor={theme.tint} size={18} />}
          </Pressable>
        </View>

        <View
          style={[
            styles.statsGrid,
            compactSpacing && styles.compactStatsGrid,
          ]}
        >
          {dashboardStats.map((stat) => (
            <View
              key={stat.id}
              style={[
                styles.statCardContainer,
                { width: compactLayout ? '100%' : '48%' },
              ]}
            >
              <StatCard stat={stat} compact={compactSpacing} />
            </View>
          ))}
        </View>
      </View>

      <View style={[styles.section, compactSpacing && styles.compactSection]}>
        <View style={styles.sectionHeader}>
          <View>
            <Text style={styles.sectionTitle}>
              Recent projects
            </Text>

            <Text style={[styles.sectionSubtitle, { color: theme.muted }]}>
              Your latest workspace activity
            </Text>
          </View>

          <View style={[styles.countBadge, { backgroundColor: `${theme.tint}18` }]}>
            <Text style={[styles.countText, { color: theme.tint }]}>{projects.length}</Text>
          </View>
        </View>

        {projectsError ? (
          <View style={[styles.notice, { backgroundColor: '#DC262614', borderColor: '#DC262640' }]}>
            <Text style={[styles.noticeText, { color: '#DC2626' }]}>{projectsError}</Text>
          </View>
        ) : recentProjects.length === 0 && !isLoadingProjects ? (
          <View style={[styles.emptyCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <Text style={styles.emptyTitle}>Your workspace is ready</Text>
            <Text style={[styles.emptyText, { color: theme.muted }]}>Create your first project from the Projects tab to start tracking your work.</Text>
          </View>
        ) : (

        <View style={[styles.projectsList, compactSpacing && styles.compactProjectsList]}>
          {recentProjects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              compact={compactSpacing}
            />
          ))}
        </View>
        )}
      </View>

      <View style={styles.footer}>
        <Text style={[styles.footerText, { color: theme.muted }]}>
          SherlskyyCommand · Mobile app
          {` v${appVersion}`}
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    flexGrow: 1,
    gap: 28,
  },
  welcomeSection: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  welcomeText: {
    flex: 1,
    gap: 6,
  },
  commandCard: {
    minHeight: 150,
    padding: 20,
    borderRadius: 24,
    flexDirection: 'row',
    justifyContent: 'space-between',
    overflow: 'hidden',
  },
  commandCopy: { flex: 1, gap: 7, paddingRight: 10 },
  commandEyebrow: { color: '#BFDBFE', fontSize: 10, fontWeight: '800', letterSpacing: 1.2 },
  commandTitle: { color: '#FFFFFF', fontSize: 21, lineHeight: 27, fontWeight: '800' },
  commandText: { color: '#DBEAFE', fontSize: 12, lineHeight: 18 },
  commandIcon: { width: 48, height: 48, borderRadius: 16, backgroundColor: '#FFFFFF22', alignItems: 'center', justifyContent: 'center' },
  greeting: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1.5,
  },
  heading: {
    fontSize: 26,
    fontWeight: '800',
  },
  subtitle: {
    fontSize: 13,
  },
  avatarContainer: {
    position: 'relative',
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '800',
  },
  databaseStatusDot: {
    position: 'absolute',
    top: -3,
    right: -3,
    width: 15,
    height: 15,
    borderRadius: 8,
    borderWidth: 2,
  },
  logoutButton: {
    width: 44,
    height: 44,
    borderWidth: 1,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  section: {
    gap: 16,
  },
  compactSection: {
    gap: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '800',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  compactStatsGrid: {
    gap: 10,
  },
  statCardContainer: {
    minWidth: 0,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  refreshButton: { width: 38, height: 38, borderRadius: 12, borderWidth: 1, alignItems: 'center', justifyContent: 'center' },
  countBadge: { minWidth: 32, height: 28, borderRadius: 14, paddingHorizontal: 9, alignItems: 'center', justifyContent: 'center' },
  countText: { fontSize: 12, fontWeight: '800' },
  sectionSubtitle: {
    fontSize: 12,
    marginTop: 5,
  },
  projectsList: {
    gap: 12,
  },
  compactProjectsList: {
    gap: 10,
  },
  notice: { borderWidth: 1, borderRadius: 16, padding: 14 },
  noticeText: { fontSize: 12, fontWeight: '600', lineHeight: 18 },
  emptyCard: { borderWidth: 1, borderRadius: 20, padding: 20, gap: 7 },
  emptyTitle: { fontSize: 15, fontWeight: '800' },
  emptyText: { fontSize: 12, lineHeight: 18 },
  footer: {
    alignItems: 'center',
    paddingTop: 8,
  },
  footerText: {
    fontSize: 11,
  },
});
