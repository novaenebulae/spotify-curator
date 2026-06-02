import { get, writable } from 'svelte/store';

import { pollJobUntilDone } from '$lib/jobPoller';
import { cancelJob, fetchJob, fetchLatestJobsByType, type Job } from '$lib/spotifyApi';

const STORAGE_KEY = 'spotify_curator_active_job';

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
	if (typeof sessionStorage === 'undefined') return;
	const payload: StoredJob = { jobId, label };
	sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

function clearPersisted(): void {
	if (typeof sessionStorage === 'undefined') return;
	sessionStorage.removeItem(STORAGE_KEY);
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

		const job = await pollJobUntilDone(jobId, (j) => {
			jobTracker.update((state) => {
				const prev = state.activeJob?.progress_current ?? 0;
				const next = Math.max(prev, j.progress_current);
				return { ...state, activeJob: { ...j, progress_current: next } };
			});
		});
		patch({
			lastJob: job,
			lastJobsByType: { ...get(jobTracker).lastJobsByType, [job.job_type]: job },
			activeJob: null,
			activeJobId: null,
			busy: false
		});
		clearPersisted();
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

/** Resume polling after navigation or full page reload. */
export async function resumeTrackedJobIfAny(): Promise<void> {
	if (typeof sessionStorage === 'undefined') return;
	const raw = sessionStorage.getItem(STORAGE_KEY);
	if (!raw) return;

	let stored: StoredJob;
	try {
		stored = JSON.parse(raw) as StoredJob;
	} catch {
		clearPersisted();
		return;
	}

	if (!stored.jobId || pollingJobId === stored.jobId) return;

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
