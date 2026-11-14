import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  View,
} from 'react-native';
import { Stack } from 'expo-router';

import { Text } from '@/components/Themed';
import { useColorScheme } from '@/components/useColorScheme';
import Colors from '@/constants/Colors';

import { apiRequest } from '@/lib/api/api-client';
import { getApiErrorMessage } from '@/lib/api/api-errors';

interface HealthResponse {
  status: string;
  database: string;
  application: string;
  version: string;
}

type ConnectionStatus = 'checking' | 'connected' | 'error';

export default function ApiHealthScreen() {
  const colorScheme = useColorScheme();
  const theme = Colors[colorScheme];

  const [status, setStatus] = useState<ConnectionStatus>('checking');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;

    async function runCheck() {
      setStatus('checking');
      setError(null);
      setHealth(null);

      try {
        const response = await apiRequest<HealthResponse>('/health');

        if (!active) return;

        if (response.status !== 'healthy') {
          throw new Error('The backend returned an unexpected health status.');
        }

        setHealth(response);
        setStatus('connected');
      } catch (requestError) {
        if (!active) return;

        setError(getApiErrorMessage(requestError));
        setStatus('error');
      }
    }

    void runCheck();

    return () => {
      active = false;
    };
  }, [attempt]);

  const statusLabel = {
    checking: 'Checking connection...',
    connected: 'Backend connected',
    error: 'Connection failed',
  }[status];

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Stack.Screen options={{ title: 'API Connection' }} />

      <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
        <Text style={styles.heading}>Backend health check</Text>

        <Text style={[styles.description, { color: theme.muted }]}>
          This screen tests the connection between your mobile application
          and the SherlskyyCommand API.
        </Text>

        <View style={styles.statusRow}>
          {status === 'checking' ? (
            <ActivityIndicator color={theme.tint} />
          ) : (
            <View
              style={[
                styles.statusIndicator,
                {
                  backgroundColor:
                    status === 'connected' ? '#16A34A' : '#DC2626',
                },
              ]}
            />
          )}

          <Text style={styles.statusText}>{statusLabel}</Text>
        </View>

        {status === 'connected' && health && (
          <View style={styles.details}>
            <Detail label="Application" value={health.application} />
            <Detail label="Database" value={health.database} />
            <Detail label="Version" value={health.version} />
          </View>
        )}

        {status === 'error' && (
          <View style={[styles.errorBox, { borderColor: '#DC2626' }]}>
            <Text style={styles.errorTitle}>Unable to connect</Text>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Retry API connection"
          disabled={status === 'checking'}
          onPress={() => setAttempt((current) => current + 1)}
          style={[
            styles.button,
            {
              backgroundColor: theme.tint,
              opacity: status === 'checking' ? 0.6 : 1,
            },
          ]}
        >
          <Text style={styles.buttonText}>
            {status === 'checking' ? 'Checking...' : 'Retry connection'}
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

interface DetailProps {
  label: string;
  value: string;
}

function Detail({ label, value }: DetailProps) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={styles.detailValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
  },
  card: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 20,
    gap: 18,
  },
  heading: {
    fontSize: 21,
    fontWeight: '800',
  },
  description: {
    fontSize: 13,
    lineHeight: 20,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 8,
  },
  statusIndicator: {
    width: 11,
    height: 11,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 15,
    fontWeight: '700',
  },
  details: {
    gap: 12,
    paddingTop: 8,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  detailLabel: {
    fontSize: 13,
    opacity: 0.7,
  },
  detailValue: {
    fontSize: 13,
    fontWeight: '700',
  },
  errorBox: {
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    gap: 6,
  },
  errorTitle: {
    color: '#DC2626',
    fontWeight: '800',
  },
  errorText: {
    fontSize: 13,
    lineHeight: 19,
  },
  button: {
    minHeight: 48,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
  },
});
