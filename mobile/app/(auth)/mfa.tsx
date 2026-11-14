import { useEffect, useState } from 'react';
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

export default function MFAScreen() {
  const router = useRouter();
  const { status, completeMFA, cancelMFA } = useAuth();

  const colorScheme = useColorScheme();
  const theme = Colors[colorScheme];

  const [code, setCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.replace('/(auth)/login');
    } else if (status === 'authenticated') {
      router.replace('/(tabs)');
    }
  }, [status, router]);

  async function handleVerification() {
    setError(null);

    const verificationCode = code.trim();

    if (!verificationCode) {
      setError('Please enter your verification code.');
      return;
    }

    try {
      setIsSubmitting(true);

      await completeMFA(verificationCode);

      router.replace('/(tabs)');
    } catch (err) {
      setError(
        getApiErrorMessage(
          err,
          'Unable to verify your code. Please try again.',
        ),
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (status !== 'mfa_required') {
    return (
      <View
        style={[
          styles.loadingContainer,
          { backgroundColor: theme.background },
        ]}
      >
        <ActivityIndicator color={theme.tint} size="large" />
      </View>
    );
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
            Verify your identity
          </Text>

          <Text style={[styles.subtitle, { color: theme.muted }]}>
            Enter the verification code from your authenticator or
            verification method to complete sign-in.
          </Text>

          <View style={styles.form}>
            <Text style={[styles.label, { color: theme.text }]}>
              Verification code
            </Text>

            <TextInput
              value={code}
              onChangeText={setCode}
              placeholder="Enter verification code"
              placeholderTextColor={theme.muted}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="number-pad"
              editable={!isSubmitting}
              maxLength={32}
              accessibilityLabel="MFA verification code"
              style={[
                styles.input,
                {
                  color: theme.text,
                  backgroundColor: theme.surface,
                  borderColor: theme.border,
                },
              ]}
            />

            {error && (
              <View
                accessibilityRole="alert"
                style={[
                  styles.errorContainer,
                  {
                    backgroundColor:
                      colorScheme === 'dark' ? '#3B1D28' : '#FEF2F2',
                  },
                ]}
              >
                <Text style={styles.errorText}>{error}</Text>
              </View>
            )}

            <Pressable
              onPress={handleVerification}
              disabled={isSubmitting}
              accessibilityRole="button"
              style={({ pressed }) => [
                styles.verifyButton,
                {
                  backgroundColor: theme.tint,
                  opacity: isSubmitting ? 0.65 : pressed ? 0.85 : 1,
                },
              ]}
            >
              {isSubmitting ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <Text style={styles.verifyButtonText}>
                  Verify and sign in
                </Text>
              )}
            </Pressable>

            <Pressable
              onPress={() => {cancelMFA();router.replace('/(auth)/login');}}
              disabled={isSubmitting}
              accessibilityRole="button"
              style={styles.backButton}
            >
              <Text style={[styles.backButtonText, { color: theme.tint }]}>
                Return to login
              </Text>
            </Pressable>
          </View>

          <Text style={[styles.footer, { color: theme.muted }]}>
            SherlskyyCommand · Secure authentication
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
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
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
    fontSize: 27,
    fontWeight: '800',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    lineHeight: 22,
    marginBottom: 30,
  },
  form: {
    gap: 18,
  },
  label: {
    fontSize: 13,
    fontWeight: '700',
    marginBottom: -9,
  },
  input: {
    height: 56,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 15,
    fontSize: 17,
    letterSpacing: 2,
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
  verifyButton: {
    height: 54,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 4,
  },
  verifyButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '800',
  },
  backButton: {
    alignItems: 'center',
    paddingVertical: 12,
  },
  backButtonText: {
    fontSize: 14,
    fontWeight: '700',
  },
  footer: {
    fontSize: 11,
    textAlign: 'center',
    marginTop: 48,
  },
});
