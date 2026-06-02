<script lang="ts">
	import JobProgress from '$lib/components/import/JobProgress.svelte';
	import { cancelTrackedJob, jobTracker } from '$lib/jobTracker';

	const showBar = $derived($jobTracker.busy || $jobTracker.activeJob != null);
</script>

{#if showBar}
	<aside class="global-job-bar" aria-live="polite">
		<JobProgress
			job={$jobTracker.activeJob}
			label={$jobTracker.label || 'Background job'}
			waiting={$jobTracker.busy && $jobTracker.activeJob == null}
			onCancel={$jobTracker.activeJobId ? cancelTrackedJob : undefined}
			cancelBusy={$jobTracker.cancelBusy}
		/>
		{#if $jobTracker.error}
			<p class="error">{$jobTracker.error}</p>
		{/if}
	</aside>
{/if}

<style>
	.global-job-bar {
		margin-bottom: var(--space-lg);
	}
	.global-job-bar :global(.card.job) {
		margin-bottom: 0;
		border-color: var(--color-accent);
		box-shadow: var(--shadow-card);
	}
</style>
