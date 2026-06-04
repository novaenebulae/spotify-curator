import { ApiClientError, parseApiErrorBody } from '$lib/apiErrors';

const BASE_URL = 'http://127.0.0.1:8765';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
	let res: Response;
	try {
		res = await fetch(`${BASE_URL}${path}`, init);
	} catch (e) {
		const hint =
			'Cannot reach the core at http://127.0.0.1:8765. Make sure Docker is running (`docker compose up`).';
		if (e instanceof TypeError) throw new Error(hint);
		throw e;
	}
	if (!res.ok) {
		let parsed = parseApiErrorBody(null, res.statusText, res.status);
		try {
			const body = await res.json();
			parsed = parseApiErrorBody(body, res.statusText, res.status);
		} catch {
			/* ignore */
		}
		throw new ApiClientError(parsed);
	}
	return (await res.json()) as T;
}

export type ModelStatusSummary = {
	total: number;
	available: number;
	missing: number;
	invalid_hash: number;
	disabled: number;
	real_inference_ready: boolean;
	default_profile: string;
};

export type ModelProfileItem = {
	name: string;
	status: string;
	available_count: number;
	missing_count: number;
	description: string;
};

export type ModelStatusItem = {
	model_key: string;
	display_name: string;
	task: string;
	status: string;
	required_for: string[];
	license?: string | null;
	local_weights_path?: string | null;
	local_metadata_path?: string | null;
	sha256?: string | null;
	expected_sha256?: string | null;
	size_bytes?: number | null;
};

export type ModelsStatusResponse = {
	summary: ModelStatusSummary;
	profiles: ModelProfileItem[];
	models: ModelStatusItem[];
	models_dir: string;
};

export type DownloadProfileResult = {
	profile: string;
	models: { model_key: string; status: string; actions?: string[] }[];
};

export function getModelsStatus(signal?: AbortSignal): Promise<ModelsStatusResponse> {
	return apiFetch<ModelsStatusResponse>('/api/v1/models/status', { signal });
}

export function downloadProfile(
	profile: string,
	opts: { accept_license: boolean; force?: boolean },
	signal?: AbortSignal
): Promise<DownloadProfileResult> {
	return apiFetch<DownloadProfileResult>('/api/v1/models/download-profile', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			profile,
			accept_license: opts.accept_license,
			force: opts.force ?? false
		}),
		signal
	});
}
