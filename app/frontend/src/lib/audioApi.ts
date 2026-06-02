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

export type AudioJobResponse = { job_id: string; status: string };

export type WorkerInfo = {
	worker_id: string;
	worker_type: string;
	status: string;
	current_job_id?: string | null;
	current_item_id?: string | null;
	last_seen_at: string | null;
};

export function downloadMissingSegments(
	opts: {
		track_ids?: number[];
		filter?: Record<string, unknown>;
		limit?: number;
		only_missing?: boolean;
		retry_failed?: boolean;
	},
	signal?: AbortSignal
): Promise<AudioJobResponse> {
	return apiFetch('/api/v1/audio/segments/download', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			track_ids: opts.track_ids,
			filter: opts.filter ?? null,
			strategy: 'hybrid_deezer_youtube_representative',
			only_missing: opts.only_missing ?? true,
			retry_failed: opts.retry_failed ?? false,
			limit: opts.limit ?? null
		}),
		signal
	});
}

export function runLowlevelAnalysis(
	opts: {
		track_ids?: number[];
		filter?: Record<string, unknown>;
		limit?: number;
		only_missing?: boolean;
		retry_failed?: boolean;
		cleanup_after?: boolean;
	},
	signal?: AbortSignal
): Promise<AudioJobResponse> {
	return apiFetch('/api/v1/audio/analysis/lowlevel', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			track_ids: opts.track_ids,
			filter: opts.filter ?? null,
			only_missing: opts.only_missing ?? true,
			retry_failed: opts.retry_failed ?? false,
			limit: opts.limit ?? null,
			cleanup_after: opts.cleanup_after ?? true,
			require_existing_segments: true
		}),
		signal
	});
}

export function cleanupAudioCache(
	opts: { dry_run?: boolean },
	signal?: AbortSignal
): Promise<{
	dry_run: boolean;
	matched_files: number;
	deleted_files: number;
	freed_bytes: number;
}> {
	return apiFetch('/api/v1/audio/cache/cleanup', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ dry_run: opts.dry_run ?? true, older_than_hours: 0, include_failed: false }),
		signal
	});
}

export function fetchWorkers(signal?: AbortSignal): Promise<{ workers: WorkerInfo[]; count: number }> {
	return apiFetch('/api/v1/workers', { signal });
}
