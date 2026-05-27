export type HealthResponse = { status: string };
export type DiagnosticsResponse = {
  env: {
    database_url_set: boolean;
    cache_dir: string;
    models_dir: string;
    logs_dir: string;
  };
  paths: Record<string, { path: string; exists: boolean; is_dir: boolean; writable: boolean }>;
};

const BASE_URL = 'http://127.0.0.1:8765';

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/health`, { signal });
  if (!res.ok) {
    throw new Error(`Healthcheck failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as HealthResponse;
}

export async function fetchDiagnostics(signal?: AbortSignal): Promise<DiagnosticsResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/diagnostics`, { signal });
  if (!res.ok) {
    throw new Error(`Diagnostics failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as DiagnosticsResponse;
}

