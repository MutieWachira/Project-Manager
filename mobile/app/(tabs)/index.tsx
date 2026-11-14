
import { useEffect, useState } from 'react';
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

import StatCard from '@/components/dashboard/StatCard';
import ProjectCard from '@/components/dashboard/ProjectCard';

import {
  dashboardStats,
  recentProjects,
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
  const appVersion = Constants.expoConfig?.version;
  const { width, height, fontScale } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const { logout } = useAuth();
  const compactLayout = width < 380 || fontScale > 1.15;
  const compactHeight = height < 720;
  const compactSpacing = compactLayout || compactHeight;
  const [databaseStatus, setDatabaseStatus] =
    useState<DatabaseStatus>('checking');
  const [isLoggingOut, setIsLoggingOut] = useState(false);

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
            Here&apos;s an overview of your projects.
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

      <View style={[styles.section, compactSpacing && styles.compactSection]}>
        <Text style={styles.sectionTitle}>
          Workspace overview
        </Text>

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

          <SymbolView
            name={{
              ios: 'arrow.up.right',
              android: 'arrow_forward',
              web: 'arrow_right',
            }}
            tintColor={theme.tint}
            size={20}
          />
        </View>

        <View
          style={[
            styles.projectsList,
            compactSpacing && styles.compactProjectsList,
          ]}
        >
          {recentProjects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              compact={compactSpacing}
            />
          ))}
        </View>
      </View>

      <View style={styles.footer}>
        <Text style={[styles.footerText, { color: theme.muted }]}>
          SherlskyyCommand · Mobile app
          {appVersion ? ` v${appVersion}` : ''}
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
  footer: {
    alignItems: 'center',
    paddingTop: 8,
  },
  footerText: {
    fontSize: 11,
  },
});
