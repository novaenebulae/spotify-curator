const BASE_URL = 'http://127.0.0.1:8765/api/v1';

export type AuthStatus = {
	connected: boolean;
	scopes: string[];
	token_expires_at: string | null;
	user: { id: string } | null;
};

export type AuthStart = {
	authorize_url: string;
	state: string;
	expires_in_seconds: number;
};

export type StageCounts = {
	pending?: number;
	running?: number;
	success?: number;
	failed?: number;
	skipped?: number;
	blocked?: number;
	cancelled?: number;
	rate_limited?: number;
};

export type Job = {
	id: string;
	job_type: string;
	status: string;
	progress_current: number;
	progress_total: number;
	current_step: string;
	result_json: Record<string, unknown>;
	last_error: string | null;
	created_at: string;
	started_at: string | null;
	finished_at: string | null;
	stages?: Record<string, StageCounts>;
};

export type JobItem = {
	id: string;
	job_id: string;
	item_type: string;
	track_id: number | null;
	segment_id: number | null;
	stage_name: string | null;
	status: string;
	error_code: string | null;
	error_message: string | null;
	result: Record<string, unknown>;
};

export type JobEvent = {
	id: number;
	job_id: string;
	item_id: string | null;
	level: string;
	event_type: string;
	message: string;
	context: Record<string, unknown>;
	created_at: string;
};

export type SnapshotMeta = {
	id: string;
	type: string;
	status: string;
	created_at: string;
	track_count: number;
	playlist_count: number;
};

export type DiffSummary = {
	liked: { added_count: number; removed_count: number };
	playlists: { added_count: number; removed_count: number; changed_count: number };
	track_status_counts: Record<string, number>;
};

export type DiffResult = {
	from_snapshot_id: string;
	to_snapshot_id: string;
	liked: { added: string[]; removed: string[] };
	playlists: {
		added: string[];
		removed: string[];
		changed: { spotify_playlist_id: string; from_item_count: number; to_item_count: number }[];
	};
	tracks: {
		statuses: {
			status: string;
			spotify_track_id: string | null;
			spotify_playlist_id: string | null;
			position: number | null;
			context: Record<string, unknown>;
		}[];
	};
	summary: DiffSummary;
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
	const res = await fetch(`${BASE_URL}${path}`, {
		...init,
		headers: {
			'Content-Type': 'application/json',
			...(init?.headers ?? {})
		}
	});
	if (!res.ok) {
		let detail = res.statusText;
		try {
			const body = await res.json();
			detail = parseApiError(body, detail);
		} catch {
			/* ignore parse errors */
		}
		throw new Error(`${detail} (${res.status})`);
	}
	if (res.status === 204) {
		return undefined as T;
	}
	return (await res.json()) as T;
}

export function fetchAuthStatus(signal?: AbortSignal): Promise<AuthStatus> {
	return apiFetch<AuthStatus>('/spotify/auth/status', { signal });
}

export function startAuth(signal?: AbortSignal): Promise<AuthStart> {
	return apiFetch<AuthStart>('/spotify/auth/start', { signal });
}

export function logout(signal?: AbortSignal): Promise<{ ok: boolean }> {
	return apiFetch<{ ok: boolean }>('/spotify/auth/logout', { method: 'POST', signal });
}

export function importLikedTracks(signal?: AbortSignal): Promise<{ job_id: string }> {
	return apiFetch<{ job_id: string }>('/spotify/import/liked-tracks', { method: 'POST', signal });
}

export function importPlaylists(signal?: AbortSignal): Promise<{ job_id: string }> {
	return apiFetch<{ job_id: string }>('/spotify/import/playlists', { method: 'POST', signal });
}

type JobApiResponse = Omit<Job, 'result_json'> & {
	result_json?: Record<string, unknown>;
	result?: Record<string, unknown>;
	stages?: Record<string, StageCounts>;
};

function normalizeJob(raw: JobApiResponse): Job {
	return {
		...raw,
		last_error: raw.last_error ?? null,
		result_json: raw.result_json ?? raw.result ?? {},
		stages: raw.stages
	};
}

export function fetchJob(jobId: string, signal?: AbortSignal): Promise<Job> {
	return apiFetch<JobApiResponse>(`/jobs/${jobId}`, { signal }).then(normalizeJob);
}

export type LatestJobsInsights = {
	jobs: Record<string, Job | null>;
};

export function fetchLatestJobsByType(signal?: AbortSignal): Promise<LatestJobsInsights> {
	return apiFetch<{ jobs: Record<string, JobApiResponse | null> }>('/jobs/insights/latest', {
		signal
	}).then((data) => ({
		jobs: Object.fromEntries(
			Object.entries(data.jobs).map(([k, v]) => [k, v ? normalizeJob(v) : null])
		)
	}));
}

export function cancelJob(jobId: string, signal?: AbortSignal): Promise<{ job_id: string; status: string }> {
	return apiFetch<{ job_id: string; status: string }>(`/jobs/${jobId}/cancel`, {
		method: 'POST',
		signal
	});
}

export function fetchJobItems(
	jobId: string,
	params?: { limit?: number; offset?: number },
	signal?: AbortSignal
): Promise<{ job_id: string; items: JobItem[]; count: number }> {
	const sp = new URLSearchParams();
	if (params?.limit != null) sp.set('limit', String(params.limit));
	if (params?.offset != null) sp.set('offset', String(params.offset));
	const qs = sp.toString();
	return apiFetch(`/jobs/${jobId}/items${qs ? `?${qs}` : ''}`, { signal });
}

export function fetchJobEvents(
	jobId: string,
	params?: { limit?: number; offset?: number; event_type?: string },
	signal?: AbortSignal
): Promise<{ job_id: string; events: JobEvent[]; count: number }> {
	const sp = new URLSearchParams();
	if (params?.limit != null) sp.set('limit', String(params.limit));
	if (params?.offset != null) sp.set('offset', String(params.offset));
	if (params?.event_type) sp.set('event_type', params.event_type);
	const qs = sp.toString();
	return apiFetch(`/jobs/${jobId}/events${qs ? `?${qs}` : ''}`, { signal });
}

export function listSnapshots(signal?: AbortSignal): Promise<SnapshotMeta[]> {
	return apiFetch<SnapshotMeta[]>('/library/snapshots', { signal });
}

export function createSnapshot(
	type: 'full' | 'liked' | 'playlists',
	signal?: AbortSignal
): Promise<{ snapshot_id: string; status: string }> {
	return apiFetch<{ snapshot_id: string; status: string }>('/library/snapshots/create', {
		method: 'POST',
		body: JSON.stringify({ type }),
		signal
	});
}

export function diffSnapshots(
	fromSnapshotId: string,
	toSnapshotId: string,
	signal?: AbortSignal
): Promise<DiffResult> {
	return apiFetch<DiffResult>('/library/snapshots/diff', {
		method: 'POST',
		body: JSON.stringify({
			from_snapshot_id: fromSnapshotId,
			to_snapshot_id: toSnapshotId
		}),
		signal
	});
}

export type ExportResult = {
	path: string;
	filename: string;
	row_count: number;
};

export function exportLikedTracks(
	format: 'csv' | 'json',
	signal?: AbortSignal
): Promise<ExportResult> {
	return apiFetch<ExportResult>('/exports/liked-tracks', {
		method: 'POST',
		body: JSON.stringify({ format }),
		signal
	});
}

export function exportPlaylists(
	format: 'csv' | 'json',
	signal?: AbortSignal
): Promise<ExportResult> {
	return apiFetch<ExportResult>('/exports/playlists', {
		method: 'POST',
		body: JSON.stringify({ format }),
		signal
	});
}

export function exportSnapshotJson(
	snapshotId: string,
	signal?: AbortSignal
): Promise<ExportResult> {
	return apiFetch<ExportResult>(`/exports/snapshot/${snapshotId}`, {
		method: 'POST',
		body: JSON.stringify({ format: 'json' }),
		signal
	});
}

export function exportDiffJson(
	fromSnapshotId: string,
	toSnapshotId: string,
	signal?: AbortSignal
): Promise<ExportResult> {
	return apiFetch<ExportResult>('/exports/diff', {
		method: 'POST',
		body: JSON.stringify({
			from_snapshot_id: fromSnapshotId,
			to_snapshot_id: toSnapshotId,
			format: 'json'
		}),
		signal
	});
}
