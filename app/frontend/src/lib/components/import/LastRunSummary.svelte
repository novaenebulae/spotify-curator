<script lang="ts">
	import type { Job } from '$lib/spotifyApi';

	type Props = {
		job: Job | null;
	};

	let { job }: Props = $props();
</script>

{#if job && (job.status === 'succeeded' || job.status === 'failed')}
	<section class="card">
		<h3>Last run</h3>
		<p>
			{job.job_type} — <strong>{job.status}</strong>
			{#if job.finished_at}
				<span class="muted"> at {job.finished_at}</span>
			{/if}
		</p>
		{#if job.status === 'failed'}
			<pre class="error">{job.last_error || 'Unknown error'}</pre>
		{:else if Object.keys(job.result_json).length > 0}
			<pre>{JSON.stringify(job.result_json, null, 2)}</pre>
		{:else}
			<p class="muted">Completed with no result payload.</p>
		{/if}
	</section>
{/if}
