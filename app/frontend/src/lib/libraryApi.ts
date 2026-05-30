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

export type TrackItem = {
	track_id: number;
	spotify_track_id: string;
	spotify_uri: string;
	title: string;
	normalized_title: string;
	artist_names: string[];
	album: {
		album_id: number;
		spotify_album_id?: string;
		name: string;
		release_date?: string;
		cover_image_url?: string | null;
		cover_image_width?: number | null;
		cover_image_height?: number | null;
	} | null;
	external_url?: string | null;
	duration_ms: number;
	isrc: string | null;
	liked: boolean;
	liked_added_at: string | null;
	is_current_liked: boolean;
	playlist_count: number;
	playlists: { playlist_id: number; name: string }[];
	availability_status: string;
	market_status: string;
	duplicate_status: string;
};

export type TracksResponse = {
	items: TrackItem[];
	pagination: { page: number; page_size: number; total: number; total_pages: number };
	sort: { field: string; order: string };
	filters: Record<string, unknown>;
};

export type TrackQuery = {
	q?: string;
	title?: string;
	artist?: string;
	album?: string;
	isrc?: string;
	liked?: boolean;
	in_any_playlist?: boolean;
	availability_status?: string;
	duplicate_status?: string;
	min_duration_ms?: number;
	max_duration_ms?: number;
	page?: number;
	page_size?: number;
	sort?: string;
	order?: string;
};

function toQuery(params: Record<string, string | number | boolean | undefined>): string {
	const sp = new URLSearchParams();
	for (const [k, v] of Object.entries(params)) {
		if (v !== undefined && v !== '') sp.set(k, String(v));
	}
	const qs = sp.toString();
	return qs ? `?${qs}` : '';
}

export async function fetchTracks(
	query: TrackQuery,
	signal?: AbortSignal
): Promise<TracksResponse> {
	return apiFetch<TracksResponse>(
		`/api/v1/tracks${toQuery(query as Record<string, string | number | boolean | undefined>)}`,
		{
			signal
		}
	);
}

export type DuplicateTrack = {
	track_id: number;
	spotify_track_id?: string;
	spotify_uri?: string;
	title: string;
	artist_names: string[];
	album_name?: string | null;
	duration_ms?: number;
	isrc: string | null;
	external_url?: string | null;
	cover_image_url?: string | null;
	occurrence_count?: number;
	contexts?: { type: string; name: string; spotify_playlist_id?: string }[];
};

export type DuplicateGroup = {
	group_id: string;
	strategy: string;
	confidence: number;
	reason: string;
	reason_label: string;
	occurrence_count: number;
	unique_track_count: number;
	is_repeated_occurrence: boolean;
	isrc: string | null;
	tracks: DuplicateTrack[];
};

export type LibrarySummary = {
	tracks_total: number;
	playlists_total: number;
	albums_total: number;
	latest_snapshot: { id: string; created_at?: string } | null;
	spotify_connected: boolean;
};

export async function fetchLibrarySummary(signal?: AbortSignal): Promise<LibrarySummary> {
	return apiFetch<LibrarySummary>('/api/v1/library/summary', { signal });
}

export async function fetchDuplicates(
	params: { strategy?: string; page?: number; page_size?: number },
	signal?: AbortSignal
) {
	return apiFetch<{
		groups: DuplicateGroup[];
		pagination: { page: number; page_size: number; total_groups: number; total_pages: number };
		summary: { group_count: number; track_count: number; by_strategy: Record<string, number> };
	}>(`/api/v1/library/duplicates${toQuery(params)}`, { signal });
}

export type MissingItem = {
	track_id: number | null;
	spotify_track_id: string | null;
	title: string | null;
	artist_names: string[];
	album_name: string | null;
	cover_image_url?: string | null;
	status: string;
	detected_at: string | null;
};

export async function fetchMissingTracks(
	params: { status?: string; page?: number; page_size?: number },
	signal?: AbortSignal
) {
	return apiFetch<{
		items: MissingItem[];
		summary: Record<string, number>;
		pagination: { page: number; page_size: number; total: number; total_pages: number };
	}>(`/api/v1/library/missing-tracks${toQuery(params)}`, { signal });
}

export type DryRunResponse = {
	action_id: number;
	dry_run: boolean;
	action_type: string;
	affected_count: number;
	affected_tracks: { track_id: number; title: string; artist_names: string[]; reason: string }[];
	warnings: { code: string; message: string }[];
	blocked: boolean;
	requires_write_scope: boolean;
	spotify_applied: boolean;
};

export async function dryRunAction(
	body: {
		action_type: string;
		track_ids?: number[];
		filter?: Record<string, unknown>;
		options?: Record<string, unknown>;
	},
	signal?: AbortSignal
): Promise<DryRunResponse> {
	return apiFetch<DryRunResponse>('/api/v1/library/actions/dry-run', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
		signal
	});
}

export type LibraryActionSummary = {
	id: number;
	action_type: string;
	dry_run: boolean;
	spotify_applied: boolean;
	status: string;
	affected_count: number;
	created_at: string | null;
};

export async function fetchLibraryActions(
	params: { action_type?: string; dry_run?: boolean; page?: number },
	signal?: AbortSignal
) {
	return apiFetch<{
		items: LibraryActionSummary[];
		pagination: { page: number; page_size: number; total: number; total_pages: number };
	}>(
		`/api/v1/library/actions${toQuery(params as Record<string, string | number | boolean | undefined>)}`,
		{
			signal
		}
	);
}

export async function fetchLibraryActionDetail(actionId: number, signal?: AbortSignal) {
	return apiFetch<LibraryActionSummary & { result: unknown; warnings: unknown[]; filter: unknown }>(
		`/api/v1/library/actions/${actionId}`,
		{ signal }
	);
}

export function formatDuration(ms: number): string {
	const s = Math.floor(ms / 1000);
	const m = Math.floor(s / 60);
	const r = s % 60;
	return `${m}:${String(r).padStart(2, '0')}`;
}
