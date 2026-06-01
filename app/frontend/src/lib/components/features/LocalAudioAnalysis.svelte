<script lang="ts">
	import { onMount } from 'svelte';
	import {
		cleanupAudioCache,
		downloadMissingSegments,
		fetchWorkers,
		runLowlevelAnalysis,
		type WorkerInfo
	} from '$lib/audioApi';
	import { fetchPreviewCoverage, resolveDeezerPreviews, type PreviewCoverage } from '$lib/previewApi';
	import { trackJob } from '$lib/jobTracker';

	let limit = $state<number | null>(10);
	let workers = $state<WorkerInfo[]>([]);
	let workersError = $state<string | null>(null);
	let previewCoverage = $state<PreviewCoverage | null>(null);
	let previewCoverageError = $state<string | null>(null);
	let actionMessage = $state<string | null>(null);
	let busy = $state(false);

	async function loadWorkers() {
		workersError = null;
		try {
			const res = await fetchWorkers();
			workers = res.workers;
		} catch (e) {
			workersError = e instanceof Error ? e.message : String(e);
		}
	}

	async function loadPreviewCoverage() {
		previewCoverageError = null;
		try {
			previewCoverage = await fetchPreviewCoverage();
		} catch (e) {
			previewCoverageError = e instanceof Error ? e.message : String(e);
		}
	}

	async function runJob(
		label: string,
		startFn: (opts: { limit?: number }) => Promise<{ job_id: string }>
	) {
		busy = true;
		actionMessage = null;
		try {
			const opts: { limit?: number } = {};
			if (limit != null) opts.limit = limit;
			const { job_id } = await startFn(opts);
			await trackJob(job_id, label);
			actionMessage = `${label} job started.`;
		} catch (e) {
			actionMessage = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
			loadWorkers();
		}
	}

	async function onCleanup(dryRun: boolean) {
		busy = true;
		actionMessage = null;
		try {
			const res = await cleanupAudioCache({ dry_run: dryRun });
			actionMessage = dryRun
				? `Dry-run: ${res.matched_files} file(s) would be removed.`
				: `Deleted ${res.deleted_files} file(s), freed ${res.freed_bytes} bytes.`;
		} catch (e) {
			actionMessage = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}

	onMount(() => {
		loadWorkers();
		loadPreviewCoverage();
		const id = setInterval(() => {
			loadWorkers();
			loadPreviewCoverage();
		}, 15000);
		return () => clearInterval(id);
	});
</script>

<section class="card local-audio">
	<h2>Local low-level analysis</h2>
	<p class="hint">
		Segments are temporary (≤30s) and removed after analysis when cleanup is enabled. Default strategy:
		hybrid Deezer preview (UI) + YouTube segments (analysis). Start workers with
		<code>docker compose --profile audio up -d</code>.
	</p>

	{#if previewCoverageError}
		<p class="error">{previewCoverageError}</p>
	{:else if previewCoverage}
		<div class="preview-coverage card-inner">
			<h3>Deezer previews (metadata)</h3>
			<p>
				{previewCoverage.with_deezer_preview} / {previewCoverage.track_count} tracks with Deezer preview
				({previewCoverage.coverage_percent}%)
			</p>
			<button
				type="button"
				disabled={busy}
				onclick={() => runJob('Resolve Deezer previews', (o) => resolveDeezerPreviews(o))}
			>
				Resolve Deezer previews
			</button>
		</div>
	{/if}

	<label class="limit-row">
		<span>Limit (tracks)</span>
		<input type="number" min="1" bind:value={limit} />
	</label>

	<div class="actions">
		<button type="button" disabled={busy} onclick={() => runJob('Audio download', downloadMissingSegments)}>
			Download missing segments
		</button>
		<button
			type="button"
			disabled={busy}
			onclick={() => runJob('Essentia low-level', runLowlevelAnalysis)}
		>
			Run low-level analysis
		</button>
		<button
			type="button"
			disabled={busy}
			onclick={() =>
				runJob('Retry local analysis', (o) =>
					runLowlevelAnalysis({ ...o, only_missing: false, retry_failed: true })
				)}
		>
			Retry failed local analysis
		</button>
		<button type="button" disabled={busy} onclick={() => onCleanup(true)}>Cleanup audio cache (dry-run)</button>
		<button type="button" disabled={busy} onclick={() => onCleanup(false)}>Cleanup audio cache</button>
	</div>

	{#if actionMessage}
		<p class="message">{actionMessage}</p>
	{/if}

	<h3>Active workers</h3>
	{#if workersError}
		<p class="error">{workersError}</p>
	{:else if workers.length === 0}
		<p class="muted">No workers reported recently. Is the <code>audio</code> Compose profile running?</p>
	{:else}
		<ul class="workers">
			{#each workers as w (w.worker_id)}
				<li><strong>{w.worker_type}</strong> — {w.status} (last seen {w.last_seen_at ?? '—'})</li>
			{/each}
		</ul>
	{/if}

	<details>
		<summary>Technical details</summary>
		<p>
			Jobs use <code>job_items</code> processed by persistent <code>audio-downloader</code> and
			<code>essentia-lowlevel-worker</code> containers. Poll job status via the summary above.
		</p>
	</details>
</section>

<style>
	.local-audio {
		margin-top: 1.5rem;
	}
	.hint {
		color: var(--muted, #666);
		font-size: 0.9rem;
	}
	.limit-row {
		display: flex;
		gap: 0.75rem;
		align-items: center;
		margin: 1rem 0;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}
	.workers {
		padding-left: 1.25rem;
	}
	.message {
		margin-top: 0.75rem;
	}
	.error {
		color: #b00020;
	}
	.muted {
		color: var(--muted, #666);
	}
</style>
