<script lang="ts">
	import { statTilesForJob, type JobRunStats } from '$lib/components/features/jobResultStats';

	type Props = {
		jobType: string;
		stats: JobRunStats;
		status?: string;
	};

	let { jobType, stats, status = '' }: Props = $props();

	const tiles = $derived(statTilesForJob(jobType, stats));
</script>

<div class="job-stats-bar" role="group" aria-label="Job run statistics">
	{#each tiles as tile (tile.key)}
		<div class="tile" class:tile-ok={tile.variant === 'ok'} class:tile-warn={tile.variant === 'warn'} class:tile-danger={tile.variant === 'danger'}>
			<span class="tile-label">{tile.label}</span>
			<span class="tile-value">{tile.value.toLocaleString()}</span>
		</div>
	{/each}
</div>
{#if status === 'cancelled'}
	<p class="cancelled-note muted">Cancelled — counts may be partial.</p>
{/if}

<style>
	.job-stats-bar {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-xs);
	}
	.tile {
		flex: 1 1 4.5rem;
		min-width: 4.5rem;
		max-width: 7rem;
		padding: 0.35rem 0.5rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		background: var(--color-surface-elevated);
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}
	.tile-label {
		font-size: 0.65rem;
		text-transform: uppercase;
		letter-spacing: 0.03em;
		color: var(--color-muted);
		line-height: 1.2;
	}
	.tile-value {
		font-size: 1rem;
		font-weight: 700;
		line-height: 1.1;
	}
	.tile-ok .tile-value {
		color: var(--color-success);
	}
	.tile-warn .tile-value {
		color: var(--color-warning);
	}
	.tile-danger .tile-value {
		color: var(--color-danger);
	}
	.cancelled-note {
		margin: var(--space-xs) 0 0;
		font-size: 0.75rem;
	}
</style>
