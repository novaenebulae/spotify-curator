<script lang="ts">
	import EnrichJobResult from '$lib/components/features/EnrichJobResult.svelte';
	import type { Job } from '$lib/spotifyApi';

	type Props = {
		job: Job | null;
	};

	let { job }: Props = $props();

	const isTerminal = $derived(
		job != null &&
			(job.status === 'succeeded' ||
				job.status === 'success' ||
				job.status === 'failed' ||
				job.status === 'cancelled')
	);

	const enrichResult = $derived(
		job?.result_json && typeof job.result_json === 'object' ? job.result_json : {}
	);

	const importStats = $derived(
		enrichResult.imported != null || enrichResult.updated != null || enrichResult.total != null
			? {
					imported: Number(enrichResult.imported ?? 0),
					updated: Number(enrichResult.updated ?? 0),
					total: Number(enrichResult.total ?? 0)
				}
			: null
	);
</script>

{#if job && isTerminal}
	<section class="card">
		<h3>Last run</h3>
		<p class="run-meta">
			<span class="job-type">{job.job_type.replace(/_/g, ' ')}</span>
			— <strong class="status-{job.status}">{job.status}</strong>
			{#if job.finished_at}
				<span class="muted"> · {new Date(job.finished_at).toLocaleString()}</span>
			{/if}
		</p>

		{#if job.status === 'failed' || job.status === 'error'}
			<p class="error-block">{job.last_error || 'Unknown error'}</p>
		{:else if job.job_type === 'reccobeats_enrichment'}
			<EnrichJobResult result={enrichResult} status={job.status} />
		{:else if importStats}
			<div class="stat-grid">
				<div class="stat-card">
					<h3>Imported</h3>
					<p class="stat-value">{importStats.imported.toLocaleString()}</p>
				</div>
				<div class="stat-card">
					<h3>Updated</h3>
					<p class="stat-value">{importStats.updated.toLocaleString()}</p>
				</div>
				<div class="stat-card">
					<h3>Total</h3>
					<p class="stat-value">{importStats.total.toLocaleString()}</p>
				</div>
			</div>
		{:else if Object.keys(enrichResult).length > 0}
			<p class="muted">Job completed. Open developer tools for raw payload if needed.</p>
		{:else}
			<p class="muted">Completed with no result payload.</p>
		{/if}
	</section>
{/if}

<style>
	.run-meta {
		margin: 0 0 var(--space-md);
	}
	.job-type {
		text-transform: capitalize;
	}
	.status-success,
	.status-succeeded {
		color: var(--color-success);
	}
	.status-failed,
	.status-error {
		color: var(--color-danger);
	}
	.status-cancelled {
		color: var(--color-warning);
	}
	.error-block {
		color: var(--color-danger);
		margin: 0;
	}
</style>
