<script lang="ts">
	import EnrichJobResult from '$lib/components/features/EnrichJobResult.svelte';
	import type { Job } from '$lib/spotifyApi';
	import { jobTracker } from '$lib/jobTracker';

	type Props = {
		job: Job | null;
	};

	let { job }: Props = $props();

	const isTerminal = (j: Job | null): boolean =>
		j != null &&
		(j.status === 'succeeded' ||
			j.status === 'success' ||
			j.status === 'partial' ||
			j.status === 'failed' ||
			j.status === 'cancelled' ||
			j.status === 'error');

	const jobsByType = $derived($jobTracker.lastJobsByType);

	function jobResult(j: Job): Record<string, unknown> {
		return j.result_json && typeof j.result_json === 'object' ? j.result_json : {};
	}

	function importStatsFor(j: Job): { imported: number; updated: number; total: number } | null {
		const r = jobResult(j);
		return r.imported != null || r.updated != null || r.total != null
			? {
					imported: Number(r.imported ?? 0),
					updated: Number(r.updated ?? 0),
					total: Number(r.total ?? 0)
				}
			: null;
	}

	function titleFor(jobType: string): string {
		if (jobType === 'reccobeats_enrichment') return 'ReccoBeats enrichment';
		if (jobType === 'audio_download') return 'Audio download (segments)';
		if (jobType === 'essentia_lowlevel_analysis') return 'Essentia low-level analysis';
		if (jobType === 'preview_resolve') return 'Deezer preview resolve';
		return jobType.replace(/_/g, ' ');
	}
</script>

{#if Object.keys(jobsByType).length > 0}
	<section class="card">
		<h3>Last runs</h3>

		{#each Object.entries(jobsByType) as [jobType, j] (jobType)}
			{#if isTerminal(j)}
				<div class="run-block">
					<p class="run-meta">
						<span class="job-type">{titleFor(jobType)}</span>
						— <strong class="status-{j.status}">{j.status}</strong>
						{#if j.finished_at}
							<span class="muted"> · {new Date(j.finished_at).toLocaleString()}</span>
						{/if}
					</p>

					{#if j.status === 'failed' || j.status === 'error'}
						<p class="error-block">{j.last_error || 'Unknown error'}</p>
					{:else if jobType === 'reccobeats_enrichment'}
						<EnrichJobResult result={jobResult(j)} status={j.status} />
					{:else}
						{#if importStatsFor(j)}
							<!-- keep legacy generic stats if present -->
							<div class="stat-grid">
								<div class="stat-card">
									<h3>Imported</h3>
									<p class="stat-value">{importStatsFor(j)?.imported.toLocaleString()}</p>
								</div>
								<div class="stat-card">
									<h3>Updated</h3>
									<p class="stat-value">{importStatsFor(j)?.updated.toLocaleString()}</p>
								</div>
								<div class="stat-card">
									<h3>Total</h3>
									<p class="stat-value">{importStatsFor(j)?.total.toLocaleString()}</p>
								</div>
							</div>
						{:else if Object.keys(jobResult(j)).length > 0}
							<details>
								<summary>Result</summary>
								<pre>{JSON.stringify(jobResult(j), null, 2)}</pre>
							</details>
						{:else}
							<p class="muted">Completed with no result payload.</p>
						{/if}
					{/if}
				</div>
			{/if}
		{/each}
	</section>
{:else if job && isTerminal(job)}
	<!-- fallback for callers still passing a single job -->
	<section class="card">
		<h3>Last run</h3>
		<p class="run-meta">
			<span class="job-type">{titleFor(job.job_type)}</span>
			— <strong class="status-{job.status}">{job.status}</strong>
			{#if job.finished_at}
				<span class="muted"> · {new Date(job.finished_at).toLocaleString()}</span>
			{/if}
		</p>
	</section>
{/if}

<style>
	.run-meta {
		margin: 0 0 var(--space-md);
	}
	.run-block + .run-block {
		margin-top: var(--space-md);
		padding-top: var(--space-md);
		border-top: 1px solid var(--color-border);
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
