
import { StyleSheet, View } from 'react-native';
import { SymbolView } from 'expo-symbols';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import { Text } from '@/components/Themed';

import type { DashboardStat } from '@/data/dashboard/dashboard-data';

const icons = {
  folder: 'folder.fill',
  activity: 'chart.bar.fill',
  check: 'checkmark.circle.fill',
  clock: 'clock.fill',
} as const;

interface StatCardProps {
  stat: DashboardStat;
  compact?: boolean;
}

export default function StatCard({
  stat,
  compact = false,
}: StatCardProps) {
  const colorScheme = useColorScheme();
  const theme = Colors[colorScheme];

  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: theme.surface,
          borderColor: theme.border,
          padding: compact ? 12 : 16,
          gap: compact ? 7 : 10,
        },
      ]}
    >
      <View style={styles.header}>
        <Text style={[styles.label, { color: theme.muted }]}>
          {stat.label}
        </Text>

        <SymbolView
          name={{
            ios: icons[stat.icon],
            android: 'circle',
            web: 'circle',
          }}
          tintColor={theme.tint}
          size={compact ? 18 : 21}
        />
      </View>

      <Text style={[styles.value, compact && styles.compactValue]}>
        {stat.value}
      </Text>

      <Text style={[styles.description, { color: theme.muted }]}>
        {stat.description}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    width: '100%',
    padding: 16,
    borderRadius: 16,
    borderWidth: 1,
    gap: 10,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 6,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    flexShrink: 1,
  },
  value: {
    fontSize: 28,
    fontWeight: '800',
  },
  compactValue: {
    fontSize: 24,
  },
  description: {
    fontSize: 11,
  },
});
