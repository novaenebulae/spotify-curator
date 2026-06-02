const BASE_URL = 'http://127.0.0.1:8765';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(`${BASE_URL}${path}`, init);
	if (!res.ok) {
		throw new Error(`API error ${res.status}`);
	}
	return (await res.json()) as T;
}

export type TrackPreview = {
	track_id: number;
	provider: string | null;
	preview_url: string | null;
	/** Same-origin stream URL for HTMLAudioElement (avoids CORB on Deezer CDN). */
	playback_url: string | null;
	match_confidence: number | null;
	is_available: boolean;
	resolve_job_id?: string | null;
};

/** Same-origin URL for HTMLAudioElement (never use Deezer CDN URLs in the browser). */
export function previewStreamUrl(trackId: number): string {
	return `${BASE_URL}/api/v1/tracks/${trackId}/preview/stream`;
}

export type PreviewCoverage = {
	track_count: number;
	with_any_preview: number;
	with_deezer_preview: number;
	missing_preview: number;
	failed_preview: number;
	coverage_percent: number;
};

export function getTrackPreview(trackId: number, resolveIfMissing = false): Promise<TrackPreview> {
	const q = resolveIfMissing ? '?resolve_if_missing=true' : '';
	return apiFetch(`/api/v1/tracks/${trackId}/preview${q}`);
}

export function fetchPreviewCoverage(): Promise<PreviewCoverage> {
	return apiFetch('/api/v1/previews/coverage');
}

export function resolveDeezerPreviews(opts: {
	only_missing?: boolean;
	force_refresh?: boolean;
	limit?: number;
}): Promise<{ job_id: string; status: string }> {
	return apiFetch('/api/v1/previews/resolve', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			only_missing: opts.only_missing ?? true,
			force_refresh: opts.force_refresh ?? false,
			limit: opts.limit ?? null
		})
	});
}
