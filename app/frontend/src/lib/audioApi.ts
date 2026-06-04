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
		analysis_mode?: 'fast' | 'precise';
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
			analysis_mode: opts.analysis_mode ?? 'fast',
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
		analysis_mode?: 'fast' | 'precise';
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
			analysis_mode: opts.analysis_mode ?? 'fast',
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

export type ModelProfileName = 'phase6-minimal' | 'phase6-recommended' | 'phase6-full';

export type AdvancedAnalysisPayload = {
	track_ids?: number[];
	filter?: Record<string, unknown>;
	only_missing?: boolean;
	force_refresh?: boolean;
	retry_failed?: boolean;
	limit?: number | null;
	analysis_mode?: 'fast' | 'precise';
	strategy?: string;
	segment_duration_seconds?: number | null;
	include_lowlevel?: boolean;
	include_tensorflow?: boolean;
	pipeline_mode?: string;
	model_profile?: ModelProfileName;
	require_real_tensorflow?: boolean;
};

export function startAdvancedAnalysis(
	opts: AdvancedAnalysisPayload,
	signal?: AbortSignal
): Promise<AudioJobResponse> {
	return apiFetch('/api/v1/audio/analysis/advanced', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			track_ids: opts.track_ids,
			filter: opts.filter ?? null,
			only_missing: opts.only_missing ?? true,
			force_refresh: opts.force_refresh ?? false,
			retry_failed: opts.retry_failed ?? false,
			limit: opts.limit ?? null,
			analysis_mode: opts.analysis_mode ?? 'fast',
			strategy: opts.strategy ?? 'hybrid_deezer_youtube_representative',
			segment_duration_seconds: opts.segment_duration_seconds ?? null,
			include_lowlevel: opts.include_lowlevel ?? true,
			include_tensorflow: opts.include_tensorflow ?? true,
			pipeline_mode: opts.pipeline_mode ?? 'streaming',
			model_profile: opts.model_profile ?? 'phase6-recommended',
			require_real_tensorflow: opts.require_real_tensorflow ?? false
		}),
		signal
	});
}
