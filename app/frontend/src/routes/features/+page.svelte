<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import CoverageCards from '$lib/components/features/CoverageCards.svelte';
	import EnrichActions from '$lib/components/features/EnrichActions.svelte';
	import FieldCoverageTable from '$lib/components/features/FieldCoverageTable.svelte';
	import LocalAudioAnalysis from '$lib/components/features/LocalAudioAnalysis.svelte';
	import RecentFailuresList from '$lib/components/features/RecentFailuresList.svelte';
	import TrackFeaturesDrawer from '$lib/components/library/TrackFeaturesDrawer.svelte';
	import JobRunSummary from '$lib/components/import/JobRunSummary.svelte';
	import type { TrackItem } from '$lib/libraryApi';
	import type { RecentFailure } from '$lib/featuresApi';
	import {
		enrichMissingReccoBeats,
		forceRefreshReccoBeats,
		getFeatureCoverage,
		retryFailedReccoBeats,
		type FeatureCoverage
	} from '$lib/featuresApi';
	import { fetchHealth } from '$lib/coreApi';
	import { getFailuresAfterParam } from '$lib/featuresApi';
	import { hydrateLastJobsFromApi, jobTracker, trackJob } from '$lib/jobTracker';

	let loading = $state(true);
	let offline = $state(false);
	let errorMessage = $state<string | null>(null);
	let coreOk = $state(false);

	let coverage = $state<FeatureCoverage | null>(null);
	let failuresPage = $state(1);
	const failuresPageSize = 20;

	let batchSize = $state(50);
	let limit = $state<number | null>(null);
	let inspectTrack: TrackItem | null = $state(null);
	let jobsInsightsLoading = $state(false);

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
				getFeatureCoverage(
					{
						include_fields: true,
						include_failed: true,
						source: 'all',
						failures_page: failuresPage,
						failures_page_size: failuresPageSize,
						failures_after: getFailuresAfterParam()
					},
					controller.signal
				)
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
			await trackJob(job_id, label, {
				onComplete: async () => {
					await loadJobsInsights();
					await loadCoverage();
				}
			});
		} catch (e) {
			jobTracker.update((s) => ({
				...s,
				error: e instanceof Error ? e.message : String(e)
			}));
		}
	}

	async function loadJobsInsights() {
		jobsInsightsLoading = true;
		await hydrateLastJobsFromApi();
		jobsInsightsLoading = false;
	}

	onMount(() => {
		void loadJobsInsights();
		loadCoverage();
	});
	function failureToTrackItem(f: RecentFailure): TrackItem {
		return {
			track_id: f.track_id,
			spotify_track_id: '',
			spotify_uri: '',
			title: f.title || `Track #${f.track_id}`,
			normalized_title: '',
			artist_names: f.artist_names,
			album: null,
			duration_ms: 0,
			isrc: null,
			liked: false,
			liked_added_at: null,
			is_current_liked: false,
			playlist_count: 0,
			playlists: [],
			availability_status: 'unknown',
			market_status: 'unknown',
			duplicate_status: 'none',
			external_url: null
		};
	}

	function inspectFailure(f: RecentFailure): void {
		inspectTrack = failureToTrackItem(f);
	}

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

		<LocalAudioAnalysis
			onJobComplete={async () => {
				await loadJobsInsights();
				await loadCoverage();
			}}
		/>
	{/if}

	{#if actionError}
		<pre class="error">{actionError}</pre>
	{/if}

	<JobRunSummary job={lastEnrichJob} loading={jobsInsightsLoading} />

	<FieldCoverageTable
		fields={coverage?.fields ?? []}
		fieldsBySource={coverage?.fields_by_source}
		{loading}
	/>
	<RecentFailuresList
		failures={coverage?.failures ?? null}
		busy={loading}
		onPageChange={(p) => {
			failuresPage = p;
			loadCoverage();
		}}
		onCleared={() => {
			failuresPage = 1;
			loadCoverage();
		}}
		onInspect={inspectFailure}
	/>
{/if}

<TrackFeaturesDrawer
	track={inspectTrack}
	open={inspectTrack !== null}
	onClose={() => (inspectTrack = null)}
/>

<style>
	.ok {
		color: var(--color-ok, #6c6);
	}
</style>
