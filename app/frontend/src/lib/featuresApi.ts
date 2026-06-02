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

export type CoverageSummary = {
	track_count: number;
	with_any_features: number;
	with_reccobeats: number;
	missing_reccobeats: number;
	failed_reccobeats: number;
	not_found_reccobeats?: number;
	with_essentia_lowlevel?: number;
	missing_essentia_lowlevel?: number;
	failed_essentia_lowlevel?: number;
	not_found_essentia_lowlevel?: number;
	coverage_percent: number;
};

export type CoverageSource = {
	source: string;
	active: boolean;
	version: string | null;
	track_count: number;
	success_count: number;
	missing_count: number;
	failed_count: number;
	not_found_count?: number;
	partial_count: number;
	coverage_percent: number;
};

export type CoverageField = {
	field: string;
	available_count: number;
	coverage_percent: number;
};

export type RecentFailure = {
	source?: string | null;
	track_id: number;
	title: string;
	artist_names: string[];
	status: string;
	error_code: string | null;
	error_message: string | null;
	occurred_at?: string | null;
};

export type CoverageFieldsBySource = {
	reccobeats: CoverageField[];
	essentia_lowlevel: CoverageField[];
};

export type FailurePage = {
	total: number;
	page: number;
	page_size: number;
	items: RecentFailure[];
};

export type FeatureCoverage = {
	summary: CoverageSummary;
	sources: CoverageSource[];
	fields: CoverageField[];
	fields_by_source?: CoverageFieldsBySource | null;
	recent_failures: RecentFailure[];
	failures?: FailurePage | null;
};

export const FAILURES_CLEARED_STORAGE_KEY = 'features_failures_cleared_at';

export function getFailuresAfterParam(): string | undefined {
	if (typeof localStorage === 'undefined') return undefined;
	return localStorage.getItem(FAILURES_CLEARED_STORAGE_KEY) ?? undefined;
}

export type EnrichPayload = {
	track_ids?: number[];
	filter?: Record<string, unknown>;
	batch_size?: number;
	only_missing?: boolean;
	retry_failed?: boolean;
	force_refresh?: boolean;
	limit?: number | null;
};

export type EnrichJobResponse = {
	job_id: string;
	status: string;
};

export async function getFeatureCoverage(
	params?: {
		source?: string;
		include_failed?: boolean;
		include_fields?: boolean;
		failures_page?: number;
		failures_page_size?: number;
		failures_after?: string;
	},
	signal?: AbortSignal
): Promise<FeatureCoverage> {
	const sp = new URLSearchParams();
	if (params?.source) sp.set('source', params.source);
	if (params?.include_failed !== undefined) sp.set('include_failed', String(params.include_failed));
	if (params?.include_fields !== undefined) sp.set('include_fields', String(params.include_fields));
	if (params?.failures_page !== undefined) sp.set('failures_page', String(params.failures_page));
	if (params?.failures_page_size !== undefined)
		sp.set('failures_page_size', String(params.failures_page_size));
	if (params?.failures_after) sp.set('failures_after', params.failures_after);
	const qs = sp.toString();
	return apiFetch<FeatureCoverage>(`/api/v1/features/coverage${qs ? `?${qs}` : ''}`, { signal });
}

export async function startReccoBeatsEnrichment(
	payload: EnrichPayload,
	signal?: AbortSignal
): Promise<EnrichJobResponse> {
	return apiFetch<EnrichJobResponse>('/api/v1/features/reccobeats/enrich', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload),
		signal
	});
}

export async function enrichMissingReccoBeats(
	opts?: { limit?: number; batch_size?: number },
	signal?: AbortSignal
): Promise<EnrichJobResponse> {
	return startReccoBeatsEnrichment(
		{ only_missing: true, retry_failed: false, force_refresh: false, ...opts },
		signal
	);
}

export async function retryFailedReccoBeats(
	opts?: { limit?: number; batch_size?: number },
	signal?: AbortSignal
): Promise<EnrichJobResponse> {
	return startReccoBeatsEnrichment(
		{ only_missing: false, retry_failed: true, force_refresh: false, ...opts },
		signal
	);
}

export async function forceRefreshReccoBeats(
	opts?: { limit?: number; batch_size?: number },
	signal?: AbortSignal
): Promise<EnrichJobResponse> {
	return startReccoBeatsEnrichment(
		{ only_missing: false, retry_failed: false, force_refresh: true, ...opts },
		signal
	);
}

export type TrackFeatureMeta = {
	pipeline_version?: string | null;
	segments_used?: number | null;
	analysis_decision?: string | null;
	external_track_id?: string | null;
};

export type TrackFeatureMerged = {
	primary_source: string;
	display_name: string;
	is_active: boolean;
	status: string;
	feature_confidence?: number | null;
	error_code?: string | null;
	error_message?: string | null;
	fields: Record<string, number>;
	meta: TrackFeatureMeta;
	fetched_at?: string | null;
};

export type TrackFeatureSource = {
	source_name: string;
	display_name: string;
	is_active: boolean;
	status: string;
	feature_confidence?: number | null;
	error_code?: string | null;
	error_message?: string | null;
	fields: Record<string, number>;
	extended: Record<string, unknown>;
	pipeline_version?: string | null;
	fetched_at?: string | null;
};

export type TrackFeaturesResponse = {
	track_id: number;
	merged: TrackFeatureMerged | null;
	sources: TrackFeatureSource[];
	availability: {
		has_any_features: boolean;
		has_reccobeats: boolean;
		has_essentia_lowlevel: boolean;
		other_sources_count: number;
	};
};

export function getTrackFeatures(
	trackId: number,
	signal?: AbortSignal
): Promise<TrackFeaturesResponse> {
	return apiFetch(`/api/v1/features/tracks/${trackId}`, { signal });
}
