import { fetchJob, type Job } from '$lib/spotifyApi';

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
	return new Promise((resolve, reject) => {
		if (signal?.aborted) {
			reject(new Error('Cancelled'));
			return;
		}
		const timer = setTimeout(() => resolve(), ms);
		signal?.addEventListener(
			'abort',
			() => {
				clearTimeout(timer);
				reject(new Error('Cancelled'));
			},
			{ once: true }
		);
	});
}

export async function pollJobUntilDone(
	jobId: string,
	onUpdate: (job: Job) => void,
	options?: { intervalMs?: number; signal?: AbortSignal }
): Promise<Job> {
	const intervalMs = options?.intervalMs ?? 750;
	for (;;) {
		const job = await fetchJob(jobId, options?.signal);
		onUpdate(job);
		if (job.status === 'succeeded' || job.status === 'failed') {
			return job;
		}
		await sleep(intervalMs, options?.signal);
	}
}
