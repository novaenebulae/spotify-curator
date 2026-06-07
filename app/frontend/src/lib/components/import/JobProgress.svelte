<script lang="ts">
	import type { Job } from '$lib/spotifyApi';

	type Props = {
		job: Job | null;
		label?: string;
		onCancel?: () => void;
		cancelBusy?: boolean;
		waiting?: boolean;
	};

	let { job, label = 'Current job', onCancel, cancelBusy = false, waiting = false }: Props =
		$props();

	const isPipeline = $derived(job?.job_type === 'audio_analysis_pipeline');
	const tp = $derived(job?.tracks_progress);
	const useTracks = $derived(isPipeline && tp != null && tp.tracks_total > 0);

	const ANALYSIS_SESSION_KEY = 'spotify_curator_analysis_session_start';

	function parseJobStartMs(j: Job | null): number | null {
		if (!j) return null;
		if (typeof sessionStorage !== 'undefined' && j.job_type === 'audio_analysis_pipeline') {
			const stored = sessionStorage.getItem(ANALYSIS_SESSION_KEY);
			if (stored) {
				const ms = Number(stored);
				if (!Number.isNaN(ms)) return ms;
			}
		}
		const createdMs = j.created_at ? Date.parse(j.created_at) : NaN;
		const startedMs = j.started_at ? Date.parse(j.started_at) : NaN;
		if (!Number.isNaN(createdMs) && !Number.isNaN(startedMs)) {
			// Stale started_at (e.g. job row reused) must not inflate elapsed time.
			if (startedMs < createdMs - 60_000 || startedMs > Date.now() + 60_000) {
				return createdMs;
			}
			return startedMs;
		}
		if (!Number.isNaN(startedMs)) return startedMs;
		if (!Number.isNaN(createdMs)) return createdMs;
		return null;
	}

	$effect(() => {
		if (job?.job_type !== 'audio_analysis_pipeline' || typeof sessionStorage === 'undefined') {
			return;
		}
		if (!sessionStorage.getItem(ANALYSIS_SESSION_KEY)) {
			sessionStorage.setItem(ANALYSIS_SESSION_KEY, String(Date.now()));
		}
	});

	const pct = $derived.by(() => {
		if (useTracks && tp) {
			const done = tp.tracks_completed + tp.tracks_failed;
			if (tp.tracks_total <= 0) return null;
			return Math.min(100, Math.round((done / tp.tracks_total) * 100));
		}
		if (!isPipeline && job && job.progress_total > 0) {
			return Math.min(100, Math.round((job.progress_current / job.progress_total) * 100));
		}
		return null;
	});

	const progressLabel = $derived.by(() => {
		if (useTracks && tp) {
			const finished = tp.tracks_completed + tp.tracks_failed;
			return `Track ${finished} / ${tp.tracks_total}`;
		}
		if (!isPipeline && job && job.progress_total > 0) {
			return `${job.progress_current.toLocaleString()} / ${job.progress_total.toLocaleString()} items`;
		}
		return null;
	});

	const itemsSubLabel = $derived.by(() => {
		if (!isPipeline || !job || job.progress_total <= 0) return null;
		return `Pipeline items: ${job.progress_current.toLocaleString()} / ${job.progress_total.toLocaleString()}`;
	});

	const elapsedText = $derived.by(() => {
		const start = parseJobStartMs(job);
		if (start == null) return null;
		const sec = Math.floor((Date.now() - start) / 1000);
		if (sec < 0 || sec > 86400 * 7) return null;
		if (sec < 60) return `${sec}s elapsed`;
		const min = Math.floor(sec / 60);
		return `${min} min ${sec % 60}s elapsed`;
	});

	const etaText = $derived.by(() => {
		if (!useTracks || !tp) return null;
		const finished = tp.tracks_completed + tp.tracks_failed;
		if (finished <= 0 || tp.tracks_pending <= 0) return null;
		const start = parseJobStartMs(job);
		if (start == null) return null;
		const elapsedMs = Date.now() - start;
		if (elapsedMs <= 0) return null;
		const etaSec = Math.round((elapsedMs / finished) * tp.tracks_pending / 1000);
		if (etaSec > 7200) return null;
		if (etaSec < 60) return `~${etaSec}s remaining`;
		return `~${Math.ceil(etaSec / 60)} min remaining`;
	});

	const isActive = $derived(
		job != null &&
			!['succeeded', 'success', 'partial', 'failed', 'cancelled', 'rate_limited', 'error'].includes(
				job.status
			)
	);
</script>

{#if job || waiting}
	<section class="card job">
		<div class="job-header">
			<h3>{label}</h3>
			{#if (isActive || waiting) && onCancel}
				<button type="button" class="secondary" disabled={cancelBusy} onclick={() => onCancel?.()}>
					Cancel job
				</button>
			{/if}
		</div>
		{#if job}
			<p>
				Status: <strong>{job.status}</strong>
				{#if job.job_type}
					<span class="muted">({job.job_type})</span>
				{/if}
			</p>
			{#if job.current_step && !(useTracks || (!isPipeline && job.progress_total > 0))}
				<p class="step">{job.current_step}</p>
			{/if}
			{#if elapsedText}
				<p class="muted timing">{elapsedText}{#if etaText} · {etaText}{/if}</p>
			{/if}
		{:else}
			<p class="muted">Starting job…</p>
		{/if}

		{#if job && (useTracks || (!isPipeline && job.progress_total > 0))}
			<div class="progress-wrap">
				<div class="progress-track">
					<div class="progress-fill" style:width="{pct ?? 0}%"></div>
				</div>
				<p class="progress-label">
					{#if pct != null}{pct}% — {/if}{progressLabel}
				</p>
				{#if itemsSubLabel}
					<p class="muted items-sub">{itemsSubLabel}</p>
				{/if}
			</div>
		{:else if (job && isActive) || waiting}
			<div class="progress-wrap indeterminate">
				<div class="progress-track">
					<div class="progress-fill indeterminate"></div>
				</div>
				<p class="progress-label muted">Working…</p>
			</div>
		{/if}

		{#if job}
			{#if job.status === 'failed' && job.last_error}
				<pre class="error">{job.last_error}</pre>
			{/if}
			{#if isPipeline && job.stages && Object.keys(job.stages).length > 0}
				<details class="stages-details">
					<summary>Pipeline stages</summary>
					<table class="stages-table">
						<thead>
							<tr>
								<th>Stage</th>
								<th>OK</th>
								<th>Failed</th>
								<th>Pending</th>
							</tr>
						</thead>
						<tbody>
							{#each Object.entries(job.stages) as [name, counts]}
								<tr>
									<td>{name.replace(/_/g, ' ')}</td>
									<td>{counts.success ?? 0}</td>
									<td>{counts.failed ?? 0}</td>
									<td>{(counts.pending ?? 0) + (counts.blocked ?? 0) + (counts.running ?? 0)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</details>
			{/if}
			{#if (job.status === 'succeeded' || job.status === 'success') && Object.keys(job.result_json).length > 0}
				<details>
					<summary>Result</summary>
					<pre>{JSON.stringify(job.result_json, null, 2)}</pre>
				</details>
			{/if}
		{/if}
	</section>
{/if}

<style>
	.job-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}
	.job-header h3 {
		margin: 0;
	}
	.timing,
	.items-sub {
		font-size: 0.85rem;
		margin: 0.25rem 0;
	}
	.stages-details {
		margin-top: 0.75rem;
	}
	.stages-table {
		width: 100%;
		font-size: 0.8rem;
		margin-top: 0.5rem;
	}
	.stages-table th,
	.stages-table td {
		text-align: left;
		padding: 0.2rem 0.4rem;
	}
</style>
