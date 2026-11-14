
import { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';

import { useAuth } from '@/components/providers/auth-provider';
import { useColorScheme } from '@/components/useColorScheme';
import Colors from '@/constants/Colors';
import { getApiErrorMessage } from '@/lib/api/api-errors';

export default function LoginScreen() {
  const router = useRouter();
  const { login } = useAuth();

  const colorScheme = useColorScheme();
  const theme = Colors[colorScheme];

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin() {
    setError(null);

    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail || !password) {
      setError('Please enter your email address and password.');
      return;
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailPattern.test(normalizedEmail)) {
      setError('Please enter a valid email address.');
      return;
    }

    try {
      setIsSubmitting(true);

      const result = await login(normalizedEmail, password);

      if (result.mfaRequired) {
            router.replace('/(auth)/mfa');
            return;
        }

      router.replace('/(tabs)');
    } catch (err) {
      setError(
        getApiErrorMessage(
          err,
          'Unable to sign in. Please try again.',
        ),
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={[
        styles.keyboardContainer,
        { backgroundColor: theme.background },
      ]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.container}>
          <View
            style={[
              styles.logoContainer,
              { backgroundColor: theme.tint },
            ]}
          >
            <Text style={styles.logoText}>S</Text>
          </View>

          <Text style={[styles.brand, { color: theme.text }]}>
            SherlskyyCommand
          </Text>

          <Text style={[styles.heading, { color: theme.text }]}>
            Welcome back
          </Text>

          <Text style={[styles.subtitle, { color: theme.muted }]}>
            Sign in to continue to your command centre.
          </Text>

          <View style={styles.form}>
            <View style={styles.inputGroup}>
              <Text style={[styles.label, { color: theme.text }]}>
                Email address
              </Text>

              <TextInput
                value={email}
                onChangeText={setEmail}
                placeholder="Enter your email"
                placeholderTextColor={theme.muted}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
                autoComplete="email"
                textContentType="emailAddress"
                editable={!isSubmitting}
                accessibilityLabel="Email address"
                style={[
                  styles.input,
                  {
                    color: theme.text,
                    backgroundColor: theme.surface,
                    borderColor: theme.border,
                  },
                ]}
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={[styles.label, { color: theme.text }]}>
                Password
              </Text>

              <View
                style={[
                  styles.passwordContainer,
                  {
                    backgroundColor: theme.surface,
                    borderColor: theme.border,
                  },
                ]}
              >
                <TextInput
                  value={password}
                  onChangeText={setPassword}
                  placeholder="Enter your password"
                  placeholderTextColor={theme.muted}
                  secureTextEntry={!showPassword}
                  autoCapitalize="none"
                  autoComplete="current-password"
                  textContentType="password"
                  editable={!isSubmitting}
                  accessibilityLabel="Password"
                  style={[
                    styles.passwordInput,
                    { color: theme.text },
                  ]}
                />

                <Pressable
                  onPress={() => setShowPassword((value) => !value)}
                  disabled={isSubmitting}
                  accessibilityRole="button"
                  accessibilityLabel={
                    showPassword ? 'Hide password' : 'Show password'
                  }
                  hitSlop={10}
                >
                  <Text style={{ color: theme.tint, fontWeight: '700' }}>
                    {showPassword ? 'Hide' : 'Show'}
                  </Text>
                </Pressable>
              </View>
            </View>

            {error && (
              <View
                accessibilityRole="alert"
                style={[
                  styles.errorContainer,
                  { backgroundColor: colorScheme === 'dark' ? '#3B1D28' : '#FEF2F2' },
                ]}
              >
                <Text style={styles.errorText}>{error}</Text>
              </View>
            )}

            <Pressable
              onPress={handleLogin}
              disabled={isSubmitting}
              accessibilityRole="button"
              style={({ pressed }) => [
                styles.loginButton,
                {
                  backgroundColor: theme.tint,
                  opacity: isSubmitting ? 0.65 : pressed ? 0.85 : 1,
                },
              ]}
            >
              {isSubmitting ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <Text style={styles.loginButtonText}>
                  Sign in
                </Text>
              )}
            </Pressable>
          </View>

          <Text style={[styles.footer, { color: theme.muted }]}>
            SherlskyyCommand · Your personal command centre
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  keyboardContainer: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  container: {
    paddingHorizontal: 24,
    paddingVertical: 48,
    width: '100%',
    maxWidth: 480,
    alignSelf: 'center',
  },
  logoContainer: {
    width: 64,
    height: 64,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
    marginBottom: 16,
  },
  logoText: {
    color: '#FFFFFF',
    fontSize: 32,
    fontWeight: '900',
  },
  brand: {
    fontSize: 17,
    fontWeight: '800',
    textAlign: 'center',
    marginBottom: 36,
  },
  heading: {
    fontSize: 29,
    fontWeight: '800',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    lineHeight: 21,
    marginBottom: 32,
  },
  form: {
    gap: 20,
  },
  inputGroup: {
    gap: 9,
  },
  label: {
    fontSize: 13,
    fontWeight: '700',
  },
  input: {
    height: 54,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 15,
    fontSize: 15,
  },
  passwordContainer: {
    minHeight: 54,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 15,
    flexDirection: 'row',
    alignItems: 'center',
  },
  passwordInput: {
    flex: 1,
    height: 52,
    fontSize: 15,
  },
  errorContainer: {
    padding: 13,
    borderRadius: 10,
  },
  errorText: {
    color: '#DC2626',
    fontSize: 13,
    lineHeight: 19,
  },
  loginButton: {
    height: 54,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 4,
  },
  loginButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '800',
  },
  footer: {
    fontSize: 11,
    textAlign: 'center',
    marginTop: 48,
  },
});
