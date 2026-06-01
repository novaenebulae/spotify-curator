<script lang="ts">
	import type { Job } from '$lib/spotifyApi';

	type Props = {
		job: Job | null;
		label?: string;
		onCancel?: () => void;
		cancelBusy?: boolean;
	};

	let { job, label = 'Current job', onCancel, cancelBusy = false }: Props = $props();

	const pct = $derived(
		job && job.progress_total > 0
			? Math.min(100, Math.round((job.progress_current / job.progress_total) * 100))
			: null
	);

	const isActive = $derived(
		job != null &&
			(job.status === 'running' ||
				job.status === 'queued' ||
				job.status === 'pending')
	);
</script>

{#if job}
	<section class="card job">
		<div class="job-header">
			<h3>{label}</h3>
			{#if isActive && onCancel}
				<button type="button" class="secondary" disabled={cancelBusy} onclick={() => onCancel?.()}>
					Cancel job
				</button>
			{/if}
		</div>
		<p>
			Status: <strong>{job.status}</strong>
			{#if job.job_type}
				<span class="muted">({job.job_type})</span>
			{/if}
		</p>
		{#if job.current_step}
			<p class="step">{job.current_step}</p>
		{/if}

		{#if job.progress_total > 0}
			<div class="progress-wrap" aria-valuenow={job.progress_current} aria-valuemax={job.progress_total}>
				<div class="progress-track">
					<div class="progress-fill" style:width="{pct ?? 0}%"></div>
				</div>
				<p class="progress-label">
					{pct}% — {job.progress_current.toLocaleString()} / {job.progress_total.toLocaleString()}
				</p>
			</div>
		{:else if isActive}
			<div class="progress-wrap indeterminate">
				<div class="progress-track">
					<div class="progress-fill indeterminate"></div>
				</div>
				<p class="progress-label muted">Working…</p>
			</div>
		{/if}

		{#if job.status === 'failed' && job.last_error}
			<pre class="error">{job.last_error}</pre>
		{/if}
		{#if (job.status === 'succeeded' || job.status === 'success') && Object.keys(job.result_json).length > 0}
			<details>
				<summary>Result</summary>
				<pre>{JSON.stringify(job.result_json, null, 2)}</pre>
			</details>
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
</style>
