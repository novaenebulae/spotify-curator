<script lang="ts">
	import CollapsibleSection from '$lib/components/common/CollapsibleSection.svelte';
	import JobRunStatsBar from '$lib/components/features/JobRunStatsBar.svelte';
	import { hasJobRunStats, jobRunStats } from '$lib/components/features/jobResultStats';
	import type { Job } from '$lib/spotifyApi';
	import { jobTracker } from '$lib/jobTracker';

	const ITEM_JOB_TYPES = new Set([
		'reccobeats_enrichment',
		'audio_download',
		'essentia_lowlevel_analysis',
		'preview_resolve'
	]);

	type Props = {
		job?: Job | null;
		loading?: boolean;
		collapsible?: boolean;
		storageKey?: string;
	};

	let {
		job = null,
		loading = false,
		collapsible = true,
		storageKey = 'features_last_runs_open'
	}: Props = $props();

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

	function formatFinished(iso: string | null | undefined): string {
		if (!iso) return '';
		try {
			return new Date(iso).toLocaleString(undefined, {
				month: 'short',
				day: 'numeric',
				hour: '2-digit',
				minute: '2-digit'
			});
		} catch {
			return iso.slice(0, 16);
		}
	}

	const ORDER = [
		'essentia_lowlevel_analysis',
		'audio_download',
		'reccobeats_enrichment',
		'preview_resolve'
	];

	const hasAnyRun = $derived(
		ORDER.some((t) => {
			const j = displayJobs[t];
			return j && isTerminal(j);
		})
	);
</script>

{#snippet runsBody()}
	{#if loading}
		<p class="muted">Loading recent jobs…</p>
	{:else if !hasAnyRun}
		<p class="muted">No completed jobs yet. Run enrichment or local analysis to see results here.</p>
	{:else}
		<ul class="runs-list">
			{#each ORDER as jobType}
				{@const j = displayJobs[jobType]}
				{#if j && isTerminal(j)}
					<li class="run-item">
						<div class="run-head">
							<span class="run-title">{titleFor(jobType)}</span>
							<span class="run-status status-{j.status}">{j.status}</span>
							{#if j.finished_at}
								<span class="run-when muted">{formatFinished(j.finished_at)}</span>
							{/if}
						</div>
						{#if j.status === 'failed' || j.status === 'error'}
							<p class="error-block">{j.last_error || 'Unknown error'}</p>
						{:else if ITEM_JOB_TYPES.has(jobType) && hasJobRunStats(jobRunStats(jobResult(j)))}
							<JobRunStatsBar jobType={jobType} stats={jobRunStats(jobResult(j))} status={j.status} />
						{:else}
							<p class="muted run-empty">No stats for this run.</p>
						{/if}
					</li>
				{/if}
			{/each}
		</ul>
	{/if}
{/snippet}

{#if collapsible}
	<CollapsibleSection title="Last runs" collapsed={true} {storageKey}>
		{@render runsBody()}
	</CollapsibleSection>
{:else}
	<section class="card last-runs-flat">
		<h3>Last runs</h3>
		{@render runsBody()}
	</section>
{/if}

<style>
	.runs-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}
	.run-item {
		padding: var(--space-sm) 0;
		border-bottom: 1px solid var(--color-border);
	}
	.run-item:last-child {
		border-bottom: none;
		padding-bottom: 0;
	}
	.run-head {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.35rem 0.5rem;
		margin-bottom: 0.35rem;
		font-size: 0.85rem;
	}
	.run-title {
		font-weight: 600;
	}
	.run-status {
		font-size: 0.8rem;
		font-weight: 600;
		text-transform: lowercase;
	}
	.run-when {
		font-size: 0.75rem;
		margin-left: auto;
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
		margin: 0 0 0.25rem;
		font-size: 0.8rem;
	}
	.run-empty {
		margin: 0;
		font-size: 0.8rem;
	}
	.last-runs-flat h3 {
		margin-top: 0;
	}
</style>
