<script lang="ts">
	import type { Job } from '$lib/spotifyApi';

	type Props = {
		job: Job | null;
		label?: string;
		onCancel?: () => void;
		cancelBusy?: boolean;
		/** Show indeterminate progress when the tracker is busy but the first poll has not returned yet. */
		waiting?: boolean;
	};

	let { job, label = 'Current job', onCancel, cancelBusy = false, waiting = false }: Props =
		$props();

	const pct = $derived(
		job && job.progress_total > 0
			? Math.min(100, Math.round((job.progress_current / job.progress_total) * 100))
			: null
	);

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
			{#if job.current_step}
				<p class="step">{job.current_step}</p>
			{/if}
		{:else}
			<p class="muted">Starting job…</p>
		{/if}

		{#if job && job.progress_total > 0}
			<div class="progress-wrap" aria-valuenow={job.progress_current} aria-valuemax={job.progress_total}>
				<div class="progress-track">
					<div class="progress-fill" style:width="{pct ?? 0}%"></div>
				</div>
				<p class="progress-label">
					{pct}% — {job.progress_current.toLocaleString()} / {job.progress_total.toLocaleString()}
				</p>
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
			{#if job.job_type === 'audio_analysis_pipeline' && job.stages && Object.keys(job.stages).length > 0}
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
