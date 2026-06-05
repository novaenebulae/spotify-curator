import type { Job } from '$lib/spotifyApi';

/** Wall-clock duration for a terminal job (started_at → finished_at, else created_at). */
export function jobRunDurationMs(job: Job): number | null {
	if (!job.finished_at) return null;
	const endMs = Date.parse(job.finished_at);
	if (Number.isNaN(endMs)) return null;

	let startMs = job.started_at ? Date.parse(job.started_at) : NaN;
	if (Number.isNaN(startMs) && job.created_at) {
		startMs = Date.parse(job.created_at);
	}
	if (Number.isNaN(startMs)) return null;

	// Reject stale or implausible started_at (same guard as JobProgress).
	if (job.created_at) {
		const createdMs = Date.parse(job.created_at);
		if (
			!Number.isNaN(createdMs) &&
			(startMs < createdMs - 60_000 || startMs > endMs + 60_000)
		) {
			startMs = createdMs;
		}
	}

	const ms = endMs - startMs;
	if (ms < 0 || ms > 7 * 86_400_000) return null;
	return ms;
}

export function formatJobRunDuration(ms: number): string {
	const sec = Math.floor(ms / 1000);
	if (sec < 60) return `${sec}s`;
	const min = Math.floor(sec / 60);
	const remSec = sec % 60;
	if (min < 60) return remSec > 0 ? `${min}m ${remSec}s` : `${min}m`;
	const hours = Math.floor(min / 60);
	const remMin = min % 60;
	return remMin > 0 ? `${hours}h ${remMin}m` : `${hours}h`;
}
