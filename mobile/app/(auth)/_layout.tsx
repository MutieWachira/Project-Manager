import { Stack } from 'expo-router';

import { useAuth } from '@/components/providers/auth-provider';

export default function AuthLayout() {
  const { status } = useAuth();

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        animation: 'slide_from_right',
      }}
    >
      <Stack.Protected
        guard={status === 'unauthenticated'}
      >
        <Stack.Screen name="login" />
      </Stack.Protected>

      <Stack.Protected
        guard={status === 'mfa_required'}
      >
        <Stack.Screen name="mfa" />
      </Stack.Protected>
    </Stack>
  );
}
