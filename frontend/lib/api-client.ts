import axios from "axios";

/**
 * Read and validate the public backend API URL.
 *
 * This value is safe to expose because it identifies the API endpoint.
 * Never put passwords, JWT secrets, or encryption keys in NEXT_PUBLIC_ variables.
 */
const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL?.trim();

if (!apiBaseUrl) {
  throw new Error(
    "NEXT_PUBLIC_API_URL is missing. Configure it in frontend/.env.local.",
  );
}

const parsedApiUrl = new URL(apiBaseUrl);

if (!["http:", "https:"].includes(parsedApiUrl.protocol)) {
  throw new Error("NEXT_PUBLIC_API_URL must use HTTP or HTTPS.");
}

/**
 * Shared Axios instance for communication with the FastAPI backend.
 */
export const apiClient = axios.create({
  baseURL: apiBaseUrl.replace(/\/+$/, ""),
  timeout: 15_000,
  withCredentials: true,
  headers: {
    Accept: "application/json",
  },
});
