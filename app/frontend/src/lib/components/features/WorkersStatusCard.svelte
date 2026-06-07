<script lang="ts">
	import { onMount } from 'svelte';
	import StatusBadge from '$lib/components/common/StatusBadge.svelte';
	import { fetchWorkers, type WorkerInfo } from '$lib/audioApi';
	import { jobTracker } from '$lib/jobTracker';

	let workers = $state<WorkerInfo[]>([]);
	let workersError = $state<string | null>(null);

	const trackerBusy = $derived($jobTracker.busy);

	const workerTypeCounts = $derived.by(() => {
		const counts = new Map<string, number>();
		for (const w of workers) {
			counts.set(w.worker_type, (counts.get(w.worker_type) ?? 0) + 1);
		}
		return [...counts.entries()].sort((a, b) => a[0].localeCompare(b[0]));
	});

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

	function stageLabel(w: WorkerInfo): string | null {
		const meta = w.metadata;
		if (meta && typeof meta === 'object' && 'stage_name' in meta) {
			const s = meta.stage_name;
			return typeof s === 'string' ? s.replace(/_/g, ' ') : null;
		}
		return null;
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

	onMount(() => {
		loadWorkers();
	});

	$effect(() => {
		const ms = trackerBusy ? 2000 : 15000;
		const id = setInterval(() => loadWorkers(), ms);
		return () => clearInterval(id);
	});
</script>

<section class="card workers-card">
	<h2>Active workers</h2>
	{#if workersError}
		<p class="error">{workersError}</p>
	{:else if workers.length === 0}
		<p class="muted">No workers reported. Start Docker profile <code>audio</code> / <code>advanced-analysis</code>.</p>
	{:else}
		{#if workerTypeCounts.length > 0}
			<p class="worker-summary muted">
				{#each workerTypeCounts as [type, count], i (type)}
					{type.replace(/_/g, ' ')} × {count}{i < workerTypeCounts.length - 1 ? ' · ' : ''}
				{/each}
			</p>
		{/if}
		<div class="worker-grid">
			{#each workers as w (w.worker_id)}
				<article class="worker-card">
					<div class="worker-card-head">
						<strong class="worker-type" title={w.worker_type}>{w.worker_type.replace(/_/g, ' ')}</strong>
						<StatusBadge variant={workerBadgeVariant(displayWorkerStatus(w))} label={displayWorkerStatus(w)} />
					</div>
					<p class="worker-meta" title={w.worker_id}>ID …{w.worker_id.slice(-10)}</p>
					{#if w.current_job_id}
						<p class="worker-meta" title={w.current_job_id}>Job …{w.current_job_id.slice(0, 10)}</p>
					{/if}
					{#if stageLabel(w)}
						<p class="worker-meta">Stage: {stageLabel(w)}</p>
					{/if}
				</article>
			{/each}
		</div>
	{/if}
	<button type="button" class="secondary" onclick={loadWorkers}>Refresh workers</button>
</section>

<style>
	.workers-card h2 {
		margin-top: 0;
	}
	.worker-summary {
		margin: 0 0 var(--space-md);
		font-size: 0.85rem;
	}
	.worker-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: var(--space-md);
		margin-bottom: var(--space-md);
	}
	.worker-card {
		min-height: 6.5rem;
		padding: var(--space-md);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		background: var(--color-surface-elevated);
	}
	.worker-card-head {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 0.5rem;
		margin-bottom: 0.35rem;
	}
	.worker-type {
		font-size: 0.9rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		flex: 1;
		min-width: 0;
	}
	.worker-meta {
		margin: 0.15rem 0 0;
		font-size: 0.8rem;
		color: var(--color-muted);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
