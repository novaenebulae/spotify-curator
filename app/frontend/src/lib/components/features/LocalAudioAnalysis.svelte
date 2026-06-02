<script lang="ts">
	import { onMount } from 'svelte';
	import StatusBadge from '$lib/components/common/StatusBadge.svelte';
	import {
		downloadMissingSegments,
		fetchWorkers,
		runLowlevelAnalysis,
		type WorkerInfo
	} from '$lib/audioApi';
	import { ApiClientError } from '$lib/apiErrors';
	import { jobTracker, trackJob } from '$lib/jobTracker';

	let {
		onJobComplete
	}: {
		onJobComplete?: () => void | Promise<void>;
	} = $props();

	let limit = $state<number | null>(10);
	let workers = $state<WorkerInfo[]>([]);
	let workersError = $state<string | null>(null);
	let actionMessage = $state<string | null>(null);
	let actionError = $state<string | null>(null);
	let actionBusy = $state(false);
	let onlyMissingSegments = $state(true);
	let useRecentLiked = $state(true);
	let analysisMode = $state<'fast' | 'precise'>('fast');

	function groupWorkers(ws: WorkerInfo[]): { worker_type: string; instances: WorkerInfo[] }[] {
		const map = new Map<string, WorkerInfo[]>();
		for (const w of ws) {
			const list = map.get(w.worker_type) ?? [];
			list.push(w);
			map.set(w.worker_type, list);
		}
		return [...map.entries()].map(([worker_type, instances]) => ({ worker_type, instances }));
	}

	const workerGroups = $derived(groupWorkers(workers));

	const trackerBusy = $derived($jobTracker.busy);

	function workerBadgeVariant(
		status: string
	): 'running' | 'idle' | 'warning' | 'neutral' {
		const s = status.toLowerCase();
		if (s === 'running') return 'running';
		if (s === 'idle') return 'idle';
		if (s === 'starting' || s === 'stopping') return 'warning';
		return 'neutral';
	}

	function displayWorkerStatus(w: WorkerInfo): string {
		if (w.status === 'idle' && w.current_job_id) return 'running';
		return w.status;
	}

	async function loadWorkers() {
		workersError = null;
		try {
			const res = await fetchWorkers();
			workers = res.workers;
		} catch (e) {
			workersError = e instanceof Error ? e.message : String(e);
		}
	}

	function trackSelectionFilter(): Record<string, unknown> | undefined {
		if (!useRecentLiked) return undefined;
		return { liked: true, sort: 'liked_added_at', order: 'desc' };
	}

	function jobOpts(): {
		analysis_mode: 'fast' | 'precise';
		limit?: number;
		only_missing?: boolean;
		filter?: Record<string, unknown>;
	} {
		const opts: {
			analysis_mode: 'fast' | 'precise';
			limit?: number;
			only_missing?: boolean;
			filter?: Record<string, unknown>;
		} = {
			analysis_mode: analysisMode,
			only_missing: onlyMissingSegments
		};
		const filter = trackSelectionFilter();
		if (filter) opts.filter = filter;
		if (limit != null && limit > 0) opts.limit = limit;
		return opts;
	}

	function noteJobOutcome(job: { status: string; last_error?: string | null }) {
		if (job.status === 'failed' || job.status === 'error') {
			actionError =
				job.last_error?.trim() ||
				'Job failed. Rebuild audio workers if Essentia errors persist, then retry with « Only missing » off.';
			actionMessage = null;
		}
	}

	function apiErrorText(e: ApiClientError): string {
		return e.message.replace(/\s*\(\d{3}\)\s*$/, '');
	}

	function formatJobError(e: unknown): string {
		if (e instanceof ApiClientError) {
			const msg = apiErrorText(e);
			if (e.code === 'NO_TRACKS') return msg;
			if (e.code === 'JOB_ALREADY_RUNNING') {
				return `${msg} Wait for the current job to finish or cancel it from the progress bar above.`;
			}
			return msg;
		}
		return e instanceof Error ? e.message : String(e);
	}

	async function runJob(
		label: string,
		startFn: (opts: {
			analysis_mode: 'fast' | 'precise';
			limit?: number;
			only_missing?: boolean;
			filter?: Record<string, unknown>;
		}) => Promise<{ job_id: string }>
	) {
		actionBusy = true;
		actionMessage = null;
		actionError = null;
		try {
			const { job_id } = await startFn(jobOpts());
			const finished = await trackJob(job_id, label, {
				onComplete: async () => {
					await loadWorkers();
					await onJobComplete?.();
				}
			});
			if (finished) noteJobOutcome(finished);
			if (!actionError) actionMessage = `${label} finished.`;
		} catch (e) {
			actionError = formatJobError(e);
		} finally {
			actionBusy = false;
			loadWorkers();
		}
	}

	async function runDownloadThenAnalyze() {
		actionBusy = true;
		actionMessage = null;
		actionError = null;
		try {
			const dl = await downloadMissingSegments(jobOpts());
			await trackJob(dl.job_id, 'Download segments', {
				onComplete: async () => {
					await loadWorkers();
				}
			});
			const an = await runLowlevelAnalysis(jobOpts());
			const finished = await trackJob(an.job_id, 'Essentia low-level', {
				onComplete: async () => {
					await loadWorkers();
					await onJobComplete?.();
				}
			});
			if (finished) noteJobOutcome(finished);
			if (!actionError) actionMessage = 'Download and low-level analysis finished.';
		} catch (e) {
			actionError = formatJobError(e);
		} finally {
			actionBusy = false;
			loadWorkers();
		}
	}

	onMount(() => {
		loadWorkers();
	});

	$effect(() => {
		const ms = trackerBusy ? 2000 : 15000;
		const id = setInterval(() => {
			loadWorkers();
		}, ms);
		return () => clearInterval(id);
	});

	$effect(() => {
		if (trackerBusy) {
			loadWorkers();
		}
	});
</script>

<section class="card local-audio">
	<h2>Local low-level analysis</h2>

	<label class="limit-row">
		<span>Limit (tracks)</span>
		<input type="number" min="1" bind:value={limit} />
	</label>

	<label class="checkbox-row">
		<input type="checkbox" bind:checked={useRecentLiked} />
		<span>Target: most recently liked tracks (matches library sort)</span>
	</label>
	<label class="checkbox-row">
		<input type="checkbox" bind:checked={onlyMissingSegments} />
		<span>Only missing (skip tracks that already have segments / local analysis)</span>
	</label>
	<label class="checkbox-row">
		<input
			type="checkbox"
			checked={analysisMode === 'precise'}
			onchange={(e) => (analysisMode = (e.currentTarget as HTMLInputElement).checked ? 'precise' : 'fast')}
		/>
		<span>Mode: {analysisMode === 'fast' ? 'Fast (1 segment)' : 'Precise (3 segments)'}</span>
	</label>

	<div class="actions">
		<button
			type="button"
			class="primary"
			disabled={actionBusy || trackerBusy}
			onclick={runDownloadThenAnalyze}
		>
			Download and analyze
		</button>
		<button
			type="button"
			disabled={actionBusy || trackerBusy}
			onclick={() =>
				runJob('Retry local analysis', (o) =>
					runLowlevelAnalysis({ ...o, only_missing: false, retry_failed: true })
				)}
		>
			Retry failed
		</button>
	</div>

	{#if actionError}
		<p class="error action-error">{actionError}</p>
	{:else if actionMessage}
		<p class="message">{actionMessage}</p>
	{/if}

	<h3>Active workers</h3>
	{#if workersError}
		<p class="error">{workersError}</p>
	{:else if workers.length === 0}
		<p class="muted">No workers reported recently. Is the <code>audio</code> Compose profile running?</p>
	{:else}
		<ul class="workers">
			{#each workerGroups as group (group.worker_type)}
				<li class="worker-row">
					<div class="worker-head">
						<strong>{group.worker_type}</strong>
						<span class="instance-count">{group.instances.length} instance(s)</span>
					</div>
					<ul class="worker-instances">
						{#each group.instances as w (w.worker_id)}
							<li>
								<StatusBadge
									variant={workerBadgeVariant(displayWorkerStatus(w))}
									label={displayWorkerStatus(w)}
								/>
								<span class="worker-meta">
									{w.worker_id.slice(-12)}
									{#if w.current_job_id}
										· job <code>{w.current_job_id.slice(0, 8)}…</code>
									{/if}
								</span>
							</li>
						{/each}
					</ul>
				</li>
			{/each}
		</ul>
	{/if}
</section>

<style>
	.local-audio {
		margin-top: 0;
	}
	.limit-row,
	.checkbox-row {
		display: flex;
		gap: 0.75rem;
		align-items: center;
		margin: 1rem 0;
	}
	.checkbox-row {
		font-size: 0.9rem;
		color: var(--color-muted);
	}
	.checkbox-row input {
		flex-shrink: 0;
	}
	.action-error {
		margin-top: 0.75rem;
		white-space: pre-wrap;
	}
	.actions .primary {
		font-weight: 600;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}
	.workers {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}
	.worker-row {
		padding: var(--space-sm) var(--space-md);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		background: var(--color-surface-elevated);
	}
	.worker-head {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		flex-wrap: wrap;
	}
	.instance-count {
		font-size: 0.8rem;
		color: var(--color-muted);
	}
	.worker-instances {
		list-style: none;
		padding: 0;
		margin: var(--space-sm) 0 0;
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}
	.worker-instances li {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		flex-wrap: wrap;
	}
	.worker-meta {
		font-size: 0.8rem;
		color: var(--color-muted);
	}
	.message {
		margin-top: 0.75rem;
	}
	.error {
		color: var(--color-danger);
	}
	.muted {
		color: var(--color-muted);
	}
</style>
