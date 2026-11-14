
import { ApiError } from './api-errors';

const configuredApiUrl = process.env.EXPO_PUBLIC_API_URL?.trim();

if (!configuredApiUrl) {
  throw new Error(
    'EXPO_PUBLIC_API_URL is missing. Check your mobile/.env.local file.',
  );
}

let parsedApiUrl: URL;

try {
  parsedApiUrl = new URL(configuredApiUrl);
} catch {
  throw new Error('EXPO_PUBLIC_API_URL is not a valid URL.');
}

if (
  parsedApiUrl.protocol !== 'http:' &&
  parsedApiUrl.protocol !== 'https:'
) {
  throw new Error('The API URL must use HTTP or HTTPS.');
}

export const API_BASE_URL = configuredApiUrl.replace(/\/+$/, '');

export function getApiWebSocketUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = new URL(`${API_BASE_URL}${normalizedPath}`);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.toString();
}

interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  accessToken?: string;
  timeoutMs?: number;
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const {
    body,
    accessToken,
    timeoutMs = 15000,
    headers: requestHeaders,
    signal: externalSignal,
    ...requestOptions
  } = options;

  const normalizedPath = path.startsWith('/') ? path : `/${path}`;

  const headers = new Headers(requestHeaders);

  headers.set('Accept', 'application/json');

  if (body !== undefined) {
    headers.set('Content-Type', 'application/json');
  }

  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  const controller = new AbortController();

  const timeout = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  const abortExternalRequest = () => controller.abort();

  externalSignal?.addEventListener('abort', abortExternalRequest);

  try {
    const response = await fetch(
      `${API_BASE_URL}${normalizedPath}`,
      {
        ...requestOptions,
        method: requestOptions.method ?? 'GET',
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      },
    );

    if (response.status === 204) {
      return undefined as T;
    }

    const responseText = await response.text();

    let responseData: unknown = null;

    if (responseText) {
      try {
        responseData = JSON.parse(responseText);
      } catch {
        responseData = responseText;
      }
    }

    if (!response.ok) {
      let message = `Request failed with status ${response.status}.`;

      if (typeof responseData === 'string' && responseData.trim()) {
        message = responseData;
      } else if (
        typeof responseData === 'object' &&
        responseData !== null
      ) {
        const errorData = responseData as {
          detail?: unknown;
          message?: unknown;
        };

        if (typeof errorData.detail === 'string') {
          message = errorData.detail;
        } else if (typeof errorData.message === 'string') {
          message = errorData.message;
        }
      }

      throw new ApiError(message, response.status, responseData);
    }

    return responseData as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (controller.signal.aborted) {
      throw new Error(
        'The API request timed out or was cancelled.',
      );
    }

    if (error instanceof Error) {
      throw new Error(`Unable to reach the API: ${error.message}`);
    }

    throw new Error('Unable to reach the API.');
  } finally {
    clearTimeout(timeout);
    externalSignal?.removeEventListener(
      'abort',
      abortExternalRequest,
    );
  }
}
