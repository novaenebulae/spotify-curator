<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import CoverageCards from '$lib/components/features/CoverageCards.svelte';
	import EnrichActions from '$lib/components/features/EnrichActions.svelte';
	import FieldCoverageTable from '$lib/components/features/FieldCoverageTable.svelte';
	import RecentFailuresList from '$lib/components/features/RecentFailuresList.svelte';
	import JobRunSummary from '$lib/components/import/JobRunSummary.svelte';
	import {
		enrichMissingReccoBeats,
		forceRefreshReccoBeats,
		getFeatureCoverage,
		retryFailedReccoBeats,
		type FeatureCoverage
	} from '$lib/featuresApi';
	import { fetchHealth } from '$lib/coreApi';
	import { jobTracker, trackJob } from '$lib/jobTracker';

	let loading = $state(true);
	let offline = $state(false);
	let errorMessage = $state<string | null>(null);
	let coreOk = $state(false);

	let coverage = $state<FeatureCoverage | null>(null);

	let batchSize = $state(50);
	let limit = $state<number | null>(null);

	const controller = new AbortController();

	const busy = $derived($jobTracker.busy);
	const actionError = $derived($jobTracker.error);
	const lastEnrichJob = $derived(
		$jobTracker.lastJob?.job_type === 'reccobeats_enrichment' ? $jobTracker.lastJob : null
	);

	async function loadCoverage() {
		loading = true;
		errorMessage = null;
		offline = false;
		try {
			const [health, cov] = await Promise.all([
				fetchHealth(controller.signal),
				getFeatureCoverage({ include_fields: true, include_failed: true }, controller.signal)
			]);
			coreOk = health.status === 'ok';
			coverage = cov;
		} catch (e) {
			const msg = e instanceof Error ? e.message : String(e);
			if (msg.includes('127.0.0.1:8765')) offline = true;
			else errorMessage = msg;
		} finally {
			loading = false;
		}
	}

	async function runEnrichment(
		startFn: (opts: { limit?: number; batch_size?: number }, signal?: AbortSignal) => Promise<{ job_id: string }>,
		label: string
	) {
		jobTracker.update((s) => ({ ...s, error: null }));
		try {
			const opts: { limit?: number; batch_size?: number } = { batch_size: batchSize };
			if (limit != null) opts.limit = limit;
			const { job_id } = await startFn(opts, controller.signal);
			await trackJob(job_id, label, { onComplete: loadCoverage });
		} catch (e) {
			jobTracker.update((s) => ({
				...s,
				error: e instanceof Error ? e.message : String(e)
			}));
		}
	}

	onMount(() => {
		loadCoverage();
	});
	onDestroy(() => controller.abort());
</script>

<div class="page-header">
	<h1>Feature enrichment</h1>
	<p class="muted">
		Enrich your library with audio features from ReccoBeats. Long operations run as background jobs.
	</p>
	<p class="muted">
		Core API: <strong class:ok={coreOk}>{coreOk ? 'Online' : loading ? '…' : 'Offline'}</strong>
		{#if lastEnrichJob}
			· Last job: <strong>{lastEnrichJob.status}</strong>
		{/if}
	</p>
</div>

{#if offline}
	<div class="error">Cannot reach the core API. Start Docker with <code>docker compose up</code>.</div>
{:else if errorMessage}
	<div class="error">{errorMessage}</div>
	<button type="button" class="secondary" onclick={loadCoverage}>Retry</button>
{:else}
	<CoverageCards {coverage} {loading} />

	{#if coverage && coverage.summary.track_count === 0}
		<section class="card">
			<p class="muted">No tracks in the library yet.</p>
			<a href="/import">Import your Spotify library first →</a>
		</section>
	{:else}
		<EnrichActions
			{busy}
			{batchSize}
			{limit}
			onBatchSizeChange={(n) => (batchSize = n)}
			onLimitChange={(n) => (limit = n)}
			onEnrichMissing={() => runEnrichment(enrichMissingReccoBeats, 'Enrich missing tracks')}
			onRetryFailed={() => runEnrichment(retryFailedReccoBeats, 'Retry failed tracks')}
			onForceRefresh={() => runEnrichment(forceRefreshReccoBeats, 'Force refresh all')}
		/>
	{/if}

	{#if actionError}
		<pre class="error">{actionError}</pre>
	{/if}

	<JobRunSummary job={lastEnrichJob} />

	<FieldCoverageTable fields={coverage?.fields ?? []} {loading} />
	<RecentFailuresList
		failures={coverage?.recent_failures ?? []}
		{busy}
		onRetry={() => runEnrichment(retryFailedReccoBeats, 'Retry failed tracks')}
	/>
{/if}

<style>
	.ok {
		color: var(--color-ok, #6c6);
	}
</style>
