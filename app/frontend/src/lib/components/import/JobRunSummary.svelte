<script lang="ts">
	import EnrichJobResult from '$lib/components/features/EnrichJobResult.svelte';
	import AudioJobResult from '$lib/components/features/AudioJobResult.svelte';
	import type { Job } from '$lib/spotifyApi';
	import { jobTracker } from '$lib/jobTracker';

	type Props = {
		job?: Job | null;
		loading?: boolean;
	};

	let { job = null, loading = false }: Props = $props();

	const isTerminal = (j: Job | null): boolean =>
		j != null &&
		(j.status === 'succeeded' ||
			j.status === 'success' ||
			j.status === 'partial' ||
			j.status === 'failed' ||
			j.status === 'cancelled' ||
			j.status === 'error');

	const jobsByType = $derived($jobTracker.lastJobsByType);

	const displayJobs = $derived.by(() => {
		const merged: Record<string, Job> = { ...jobsByType };
		if (job && isTerminal(job)) {
			const existing = merged[job.job_type];
			if (!existing || !existing.finished_at || (job.finished_at && job.finished_at > existing.finished_at)) {
				merged[job.job_type] = job;
			}
		}
		return merged;
	});

	const latestLocalAnalysis = $derived.by(() => {
		const dl = displayJobs['audio_download'];
		const ess = displayJobs['essentia_lowlevel_analysis'];
		const candidates = [dl, ess].filter((j): j is Job => j != null && !!j.finished_at);
		if (candidates.length === 0) return null;
		return candidates.sort((a, b) => (b.finished_at ?? '').localeCompare(a.finished_at ?? ''))[0];
	});

	function jobResult(j: Job): Record<string, unknown> {
		return j.result_json && typeof j.result_json === 'object' ? j.result_json : {};
	}

	function titleFor(jobType: string): string {
		if (jobType === 'reccobeats_enrichment') return 'ReccoBeats enrichment';
		if (jobType === 'audio_download') return 'Audio download (segments)';
		if (jobType === 'essentia_lowlevel_analysis') return 'Essentia low-level analysis';
		if (jobType === 'preview_resolve') return 'Deezer preview resolve';
		return jobType.replace(/_/g, ' ');
	}

	const ORDER = [
		'essentia_lowlevel_analysis',
		'audio_download',
		'reccobeats_enrichment',
		'preview_resolve'
	];
</script>

<section class="card last-runs">
	<h3>Last runs</h3>

	{#if loading}
		<p class="muted">Loading recent jobs…</p>
	{:else if latestLocalAnalysis}
		<div class="highlight-run">
			<p class="run-meta">
				<strong>Latest local analysis</strong> —
				{titleFor(latestLocalAnalysis.job_type)}
				· <span class="status-{latestLocalAnalysis.status}">{latestLocalAnalysis.status}</span>
				{#if latestLocalAnalysis.finished_at}
					<span class="muted"> · {new Date(latestLocalAnalysis.finished_at).toLocaleString()}</span>
				{/if}
			</p>
			<AudioJobResult result={jobResult(latestLocalAnalysis)} status={latestLocalAnalysis.status} />
		</div>
	{/if}

	{#if Object.keys(displayJobs).length === 0}
		{#if !loading}
			<p class="muted">No completed jobs yet. Run enrichment or local analysis to see results here.</p>
		{/if}
	{:else}
		{#each ORDER as jobType}
			{@const j = displayJobs[jobType]}
			{#if j && isTerminal(j)}
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
					{:else if jobType === 'audio_download' || jobType === 'essentia_lowlevel_analysis'}
						<AudioJobResult result={jobResult(j)} status={j.status} />
					{:else if Object.keys(jobResult(j)).length > 0}
						<details>
							<summary>Result</summary>
							<pre>{JSON.stringify(jobResult(j), null, 2)}</pre>
						</details>
					{:else}
						<p class="muted">Completed with no result payload.</p>
					{/if}
				</div>
			{/if}
		{/each}
	{/if}
</section>

<style>
	.last-runs h3 {
		margin-top: 0;
	}
	.highlight-run {
		margin-bottom: var(--space-md);
		padding-bottom: var(--space-md);
		border-bottom: 1px solid var(--color-border);
	}
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
	.status-cancelled,
	.status-partial {
		color: var(--color-warning);
	}
	.error-block {
		color: var(--color-danger);
		margin: 0;
	}
</style>
