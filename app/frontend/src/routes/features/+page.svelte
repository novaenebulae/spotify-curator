<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import CoverageCards from '$lib/components/features/CoverageCards.svelte';
	import EnrichActions from '$lib/components/features/EnrichActions.svelte';
	import LocalAnalysisPanel from '$lib/components/features/LocalAnalysisPanel.svelte';
	import WorkersStatusCard from '$lib/components/features/WorkersStatusCard.svelte';
	import ModelsStatusPanel from '$lib/components/features/ModelsStatusPanel.svelte';
	import RecentFailuresList from '$lib/components/features/RecentFailuresList.svelte';
	import TrackFeaturesDrawer from '$lib/components/library/TrackFeaturesDrawer.svelte';
	import JobRunSummary from '$lib/components/import/JobRunSummary.svelte';
	import type { TrackItem } from '$lib/libraryApi';
	import {
		enrichMissingReccoBeats,
		forceRefreshReccoBeats,
		getFeatureCoverage,
		getAdvancedCoverage,
		retryFailedReccoBeats,
		getFailuresAfterParam,
		type FeatureCoverage,
		type AdvancedCoverage,
		type RecentFailure
	} from '$lib/featuresApi';
	import { getModelsStatus, type ModelsStatusResponse } from '$lib/modelsApi';
	import { fetchHealth } from '$lib/coreApi';
	import { hydrateLastJobsFromApi, jobTracker, trackJob } from '$lib/jobTracker';

	let loading = $state(true);
	let offline = $state(false);
	let errorMessage = $state<string | null>(null);
	let coreOk = $state(false);

	let coverage = $state<FeatureCoverage | null>(null);
	let advancedCoverage = $state<AdvancedCoverage | null>(null);
	let modelsStatus = $state<ModelsStatusResponse | null>(null);
	let modelsError = $state<string | null>(null);
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

	async function loadModels() {
		modelsError = null;
		try {
			modelsStatus = await getModelsStatus(controller.signal);
		} catch (e) {
			modelsError = e instanceof Error ? e.message : String(e);
		}
	}

	async function loadAdvancedCoverage() {
		try {
			advancedCoverage = await getAdvancedCoverage(
				{ recent_failures_limit: 1 },
				controller.signal
			);
		} catch {
			/* optional for coverage tiles */
		}
	}

	async function loadCoverage() {
		loading = true;
		errorMessage = null;
		offline = false;
		try {
			const [health, cov] = await Promise.all([
				fetchHealth(controller.signal),
				getFeatureCoverage(
					{
						include_fields: false,
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

	function scheduleDeferredLoads() {
		const run = () => {
			void loadAdvancedCoverage();
			void loadModels();
		};
		if (typeof requestIdleCallback !== 'undefined') {
			requestIdleCallback(run, { timeout: 2000 });
		} else {
			setTimeout(run, 0);
		}
	}

	async function reloadAll() {
		await loadCoverage();
		await Promise.all([loadAdvancedCoverage(), loadModels()]);
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
					await reloadAll();
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
		void loadCoverage().then(() => scheduleDeferredLoads());
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
		Enrich your library with ReccoBeats and local analysis (Essentia low-level + TensorFlow pipeline).
		Long operations run as background jobs.
	</p>
	<p class="muted">
		Core API: <strong class:ok={coreOk}>{coreOk ? 'Online' : loading ? '…' : 'Offline'}</strong>
		{#if lastEnrichJob}
			· Last ReccoBeats job: <strong>{lastEnrichJob.status}</strong>
		{/if}
	</p>
</div>

{#if offline}
	<div class="error">Cannot reach the core API. Start Docker with <code>docker compose up</code>.</div>
{:else if errorMessage}
	<div class="error">{errorMessage}</div>
	<button type="button" class="secondary" onclick={reloadAll}>Retry</button>
{:else}
	<h2 class="section-title">Features coverage</h2>
	<CoverageCards {coverage} {advancedCoverage} {loading} />

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

		<LocalAnalysisPanel
			{busy}
			modelsStatus={modelsStatus}
			onJobComplete={async () => {
				await loadJobsInsights();
				await reloadAll();
			}}
		/>

		<WorkersStatusCard />

		<ModelsStatusPanel
			status={modelsStatus}
			loading={loading}
			error={modelsError}
			onRefresh={loadModels}
		/>

		<JobRunSummary job={lastEnrichJob} loading={jobsInsightsLoading} />
	{/if}

	{#if actionError}
		<pre class="error">{actionError}</pre>
	{/if}

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
	.section-title {
		font-size: 1rem;
		margin: var(--space-lg) 0 var(--space-sm);
		font-weight: 600;
	}
</style>
