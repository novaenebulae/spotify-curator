const BASE_URL = 'http://127.0.0.1:8765';

function parseApiError(body: unknown, fallback: string): string {
	if (body && typeof body === 'object') {
		const record = body as Record<string, unknown>;
		const err = record.error;
		if (err && typeof err === 'object') {
			const msg = (err as { message?: string }).message;
			if (msg) return msg;
		}
	}
	return fallback;
}

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
		let detail = res.statusText;
		try {
			const body = await res.json();
			detail = parseApiError(body, detail);
		} catch {
			/* ignore */
		}
		throw new Error(`${detail} (${res.status})`);
	}
	return (await res.json()) as T;
}

export type ValidationIssue = {
	code: string;
	message: string;
	path?: string | null;
};

export type ValidateResponse = {
	valid: boolean;
	errors: ValidationIssue[];
	warnings: ValidationIssue[];
	normalized_rule?: Record<string, unknown> | null;
};

export type Preset = {
	id: string;
	label: string;
	description?: string;
	rule: Record<string, unknown>;
	warnings?: string[];
};

export type PreviewItem = {
	track_id: number;
	position: number;
	final_score: number;
	title?: string;
	artist_names?: string[];
	spotify_track_id?: string | null;
};

export type PreviewResponse = {
	generated_playlist_id: number;
	items: PreviewItem[];
	exclusions: unknown[];
	summary: {
		candidate_count: number;
		selected_count: number;
		excluded_count: number;
		warnings: string[];
	};
	warnings: string[];
	dry_run: boolean;
};

export type DryRunSyncResponse = {
	sync_job_id: number;
	dry_run: boolean;
	mode: string;
	diff: { to_add: string[]; to_remove: string[]; unchanged: string[] };
	warnings: string[];
};

export async function fetchPresets(signal?: AbortSignal): Promise<Preset[]> {
	const data = await apiFetch<{ presets: Preset[] }>('/api/v1/playlist-rules/presets', { signal });
	return data.presets;
}

export async function validateRule(
	rule: Record<string, unknown>,
	signal?: AbortSignal
): Promise<ValidateResponse> {
	return apiFetch<ValidateResponse>('/api/v1/playlist-rules/validate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ rule }),
		signal
	});
}

export async function createPreview(
	body: { rule_id?: number; rule?: Record<string, unknown> },
	signal?: AbortSignal
): Promise<PreviewResponse> {
	return apiFetch<PreviewResponse>('/api/v1/generated-playlists/preview', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
		signal
	});
}

export async function syncDryRun(
	body: {
		generated_playlist_id: number;
		target_spotify_playlist_id?: string | null;
		sync_mode?: string;
	},
	signal?: AbortSignal
): Promise<DryRunSyncResponse> {
	return apiFetch<DryRunSyncResponse>('/api/v1/sync/dry-run', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
		signal
	});
}
