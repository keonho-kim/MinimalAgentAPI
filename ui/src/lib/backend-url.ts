declare const __MINIAL_AGENT_BACKEND_SERVER_URL__: string | undefined;

const INJECTED_BACKEND_SERVER_URL =
  typeof __MINIAL_AGENT_BACKEND_SERVER_URL__ === "string"
    ? __MINIAL_AGENT_BACKEND_SERVER_URL__
    : "";

export const BACKEND_SERVER_URL = normalizeBackendServerUrl(
  INJECTED_BACKEND_SERVER_URL,
);

export function apiUrl(path: string) {
  return resolveBackendUrl(path, BACKEND_SERVER_URL);
}

export function apiResourceUrl(url: string | null) {
  if (!url) {
    return null;
  }
  return resolveBackendUrl(url, BACKEND_SERVER_URL);
}

export function resolveBackendUrl(path: string, backendServerUrl: string) {
  if (isAbsoluteUrl(path)) {
    return path;
  }

  const normalizedBase = normalizeBackendServerUrl(backendServerUrl);
  if (!normalizedBase) {
    return path;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

export function normalizeBackendServerUrl(value: string) {
  return value.trim().replace(/\/+$/, "");
}

function isAbsoluteUrl(value: string) {
  return /^[a-z][a-z0-9+.-]*:\/\//i.test(value);
}
