import * as SecureStore from 'expo-secure-store';

const REFRESH_TOKEN_KEY = 'sherlskyycommand.refresh_token';

/**
 * Securely saves the refresh token on the device.
 * Never log the token or include it in error messages.
 */
export async function saveRefreshToken(token: string): Promise<void> {
  if (!token || !token.trim()) {
    throw new Error('A valid refresh token is required.');
  }

  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token);
}

/**
 * Retrieves the saved refresh token.
 * Returns null when no token is stored.
 */
export async function getRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
}

/**
 * Deletes the saved refresh token from the device.
 */
export async function deleteRefreshToken(): Promise<void> {
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
}

/**
 * Checks whether a refresh token is currently stored.
 */
export async function hasRefreshToken(): Promise<boolean> {
  const token = await getRefreshToken();
  return token !== null && token.length > 0;
}
