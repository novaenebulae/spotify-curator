import { get, writable } from 'svelte/store';

import { pollJobUntilDone } from '$lib/jobPoller';
import {
	cancelJob,
	fetchJob,
	fetchLatestJobsByType,
	fetchRunningJobs,
	type Job
} from '$lib/spotifyApi';

const STORAGE_KEY = 'spotify_curator_active_job';
const LOCAL_STORAGE_KEY = 'spotify_curator_active_job_backup';

const TRACKED_RUNNING_JOB_TYPES = [
	'audio_analysis_pipeline',
	'reccobeats_enrichment',
	'audio_download',
	'essentia_lowlevel_analysis',
	'preview_resolve'
] as const;

const RUNNING_JOB_LABELS: Record<string, string> = {
	audio_analysis_pipeline: 'Advanced audio pipeline',
	reccobeats_enrichment: 'ReccoBeats enrichment',
	audio_download: 'Audio download',
	essentia_lowlevel_analysis: 'Essentia low-level analysis',
	preview_resolve: 'Preview resolve'
};

type StoredJob = {
	jobId: string;
	label: string;
};

export type JobTrackerState = {
	activeJob: Job | null;
	activeJobId: string | null;
	lastJob: Job | null;
	lastJobsByType: Record<string, Job>;
	busy: boolean;
	label: string;
	cancelBusy: boolean;
	error: string | null;
};

const initialState: JobTrackerState = {
	activeJob: null,
	activeJobId: null,
	lastJob: null,
	lastJobsByType: {},
	busy: false,
	label: '',
	cancelBusy: false,
	error: null
};

export const jobTracker = writable<JobTrackerState>(initialState);

let pollingJobId: string | null = null;

function patch(partial: Partial<JobTrackerState>): void {
	jobTracker.update((state) => ({ ...state, ...partial }));
}

function persistActive(jobId: string, label: string): void {
	const payload: StoredJob = { jobId, label };
	const raw = JSON.stringify(payload);
	if (typeof sessionStorage !== 'undefined') {
		sessionStorage.setItem(STORAGE_KEY, raw);
	}
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem(LOCAL_STORAGE_KEY, raw);
	}
}

function readPersisted(): StoredJob | null {
	const sources: Storage[] = [];
	if (typeof sessionStorage !== 'undefined') sources.push(sessionStorage);
	if (typeof localStorage !== 'undefined') sources.push(localStorage);
	for (const storage of sources) {
		const raw = storage.getItem(STORAGE_KEY) ?? storage.getItem(LOCAL_STORAGE_KEY);
		if (!raw) continue;
		try {
			return JSON.parse(raw) as StoredJob;
		} catch {
			storage.removeItem(STORAGE_KEY);
			storage.removeItem(LOCAL_STORAGE_KEY);
		}
	}
	return null;
}

function clearPersisted(): void {
	if (typeof sessionStorage !== 'undefined') {
		sessionStorage.removeItem(STORAGE_KEY);
	}
	if (typeof localStorage !== 'undefined') {
		localStorage.removeItem(LOCAL_STORAGE_KEY);
	}
}

const TERMINAL = new Set([
	'succeeded',
	'success',
	'partial',
	'failed',
	'cancelled',
	'rate_limited',
	'error'
]);

function isTerminal(status: string): boolean {
	return TERMINAL.has(status);
}

/**
 * Poll a background job until completion. Survives route changes (module singleton).
 */
export async function trackJob(
	jobId: string,
	label: string,
	options?: { onComplete?: (job: Job) => void | Promise<void> }
): Promise<Job | void> {
	if (pollingJobId === jobId) return;

	pollingJobId = jobId;
	persistActive(jobId, label);
	patch({
		activeJobId: jobId,
		busy: true,
		label,
		error: null,
		activeJob: null
	});

	try {
		const initialJob = await fetchJob(jobId);
		patch({ activeJob: initialJob });

		await pollJobUntilDone(jobId, (j) => {
			jobTracker.update((state) => {
				const sameJob = state.activeJob?.id === j.id;
				const prev = sameJob ? (state.activeJob?.progress_current ?? 0) : 0;
				const next = Math.max(prev, j.progress_current);
				return { ...state, activeJob: { ...j, progress_current: next } };
			});
		});
		const job = await fetchJob(jobId);
		patch({
			lastJob: job,
			lastJobsByType: { ...get(jobTracker).lastJobsByType, [job.job_type]: job },
			activeJob: null,
			activeJobId: null,
			busy: false
		});
		clearPersisted();
		if (
			job.job_type === 'audio_analysis_pipeline' &&
			typeof sessionStorage !== 'undefined' &&
			['succeeded', 'success', 'partial', 'failed', 'cancelled'].includes(job.status)
		) {
			sessionStorage.removeItem('spotify_curator_analysis_session_start');
		}
		await options?.onComplete?.(job);
		return job;
	} catch (e) {
		const msg = e instanceof Error ? e.message : String(e);
		patch({
			error: msg,
			busy: false,
			activeJob: null,
			activeJobId: null
		});
		clearPersisted();
	} finally {
		if (pollingJobId === jobId) {
			pollingJobId = null;
		}
	}
}

export async function cancelTrackedJob(): Promise<void> {
	const { activeJobId } = get(jobTracker);
	if (!activeJobId) return;
	patch({ cancelBusy: true, error: null });
	try {
		await cancelJob(activeJobId);
	} catch (e) {
		patch({
			error: e instanceof Error ? e.message : String(e),
			cancelBusy: false
		});
		return;
	}
	patch({ cancelBusy: false });
}

function mergeJobMaps(
	current: Record<string, Job>,
	incoming: Record<string, Job | null>
): Record<string, Job> {
	const merged = { ...current };
	for (const [jobType, job] of Object.entries(incoming)) {
		if (!job || !isTerminal(job.status)) continue;
		const existing = merged[jobType];
		if (!existing?.finished_at || (job.finished_at && job.finished_at > existing.finished_at)) {
			merged[jobType] = job;
		}
	}
	return merged;
}

/** Load latest terminal jobs from API (survives page reload). */
export async function hydrateLastJobsFromApi(): Promise<void> {
	try {
		const { jobs } = await fetchLatestJobsByType();
		const normalized: Record<string, Job> = {};
		for (const [k, v] of Object.entries(jobs)) {
			if (v) normalized[k] = v;
		}
		patch({
			lastJobsByType: mergeJobMaps(get(jobTracker).lastJobsByType, normalized)
		});
	} catch {
		/* offline or API unavailable */
	}
}

/** Resume an active job from API when browser storage is empty (e.g. after reload). */
export async function hydrateActiveJobFromApi(): Promise<void> {
	if (pollingJobId || get(jobTracker).busy) return;
	try {
		const jobs = await fetchRunningJobs({ limit: 50 });
		const candidates = jobs
			.filter((job) => TRACKED_RUNNING_JOB_TYPES.includes(job.job_type as (typeof TRACKED_RUNNING_JOB_TYPES)[number]))
			.sort((a, b) => {
				const ta = a.created_at ? Date.parse(a.created_at) : 0;
				const tb = b.created_at ? Date.parse(b.created_at) : 0;
				return tb - ta;
			});
		const active = candidates[0];
		if (!active || pollingJobId === active.id) return;
		void trackJob(active.id, RUNNING_JOB_LABELS[active.job_type] ?? 'Background job');
	} catch {
		/* offline or API unavailable */
	}
}

/** Resume polling after navigation or full page reload. */
export async function resumeTrackedJobIfAny(): Promise<void> {
	const stored = readPersisted();
	if (!stored?.jobId || pollingJobId === stored.jobId) return;

	try {
		const job = await fetchJob(stored.jobId);
		if (isTerminal(job.status)) {
			patch({
				lastJob: job,
				lastJobsByType: { ...get(jobTracker).lastJobsByType, [job.job_type]: job },
				busy: false,
				activeJob: null,
				activeJobId: null
			});
			clearPersisted();
			return;
		}
		void trackJob(stored.jobId, stored.label || 'Background job');
	} catch {
		clearPersisted();
	}
}
