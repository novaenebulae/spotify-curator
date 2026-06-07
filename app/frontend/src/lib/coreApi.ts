import { API_ORIGIN, coreOfflineMessage } from '$lib/apiBase';

export type HealthResponse = {
	status: string;
	service?: string;
	version?: string;
};

export type RuntimeConfigResponse = {
	api_base_url: string;
	database_configured: boolean;
	spotify_client_id_configured: boolean;
	export_dir: string;
	cache_dir: string;
	data_dir?: string;
	app_version?: string;
};

export type DockerCheckItem = {
	id: string;
	check_name: string;
	command: string;
	exit_code: number | null;
	stdout: string | null;
	stderr: string | null;
	success: boolean;
	created_at: string;
};

export type DiagnosticsResponse = {
	env: {
		database_url_set: boolean;
		cache_dir: string;
		models_dir: string;
		logs_dir: string;
		export_dir?: string;
		api_version?: string;
	};
	paths: Record<string, { path: string; exists: boolean; is_dir: boolean; writable: boolean }>;
	recent_docker_checks?: DockerCheckItem[];
};

function parseApiError(body: unknown, fallback: string): string {
	if (body && typeof body === 'object') {
		const record = body as Record<string, unknown>;
		const err = record.error;
		if (err && typeof err === 'object') {
			const msg = (err as { message?: string }).message;
			if (msg) return msg;
		}
		if (typeof record.detail === 'string') return record.detail;
	}
	return fallback;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
	let res: Response;
	try {
		res = await fetch(`${API_ORIGIN}${path}`, init);
	} catch (e) {
		const hint = coreOfflineMessage();
		if (e instanceof TypeError) {
			throw new Error(hint);
		}
		throw e;
	}
	if (!res.ok) {
		let detail = res.statusText;
		try {
			const body = await res.json();
			detail = parseApiError(body, detail);
		} catch {
			/* ignore */
		}
		throw new Error(`${detail} (${res.status})`);
	}
	if (res.status === 204) {
		return undefined as T;
	}
	return (await res.json()) as T;
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
	return apiFetch<HealthResponse>('/api/v1/health', { signal });
}

export async function fetchRuntimeConfig(signal?: AbortSignal): Promise<RuntimeConfigResponse> {
	return apiFetch<RuntimeConfigResponse>('/api/v1/runtime/config', { signal });
}

export async function fetchDockerChecks(
	signal?: AbortSignal
): Promise<{ items: DockerCheckItem[] }> {
	return apiFetch<{ items: DockerCheckItem[] }>('/api/v1/runtime/docker/checks', { signal });
}

export async function runDockerChecks(
	signal?: AbortSignal
): Promise<{ job_id: string; status: string }> {
	return apiFetch<{ job_id: string; status: string }>('/api/v1/runtime/docker/checks/run', {
		method: 'POST',
		signal
	});
}

export async function fetchDiagnostics(signal?: AbortSignal): Promise<DiagnosticsResponse> {
	return apiFetch<DiagnosticsResponse>('/api/v1/diagnostics', { signal });
}
