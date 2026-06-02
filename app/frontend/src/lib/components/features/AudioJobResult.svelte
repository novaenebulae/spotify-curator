<script lang="ts">
	type Props = {
		result: Record<string, unknown>;
		status: string;
	};

	let { result, status }: Props = $props();

	const trackCount = $derived(Number(result.track_count ?? 0));
	const segmentsCreated = $derived(Number(result.segments_created ?? 0));
	const segmentsPlanned = $derived(Number(result.segments_planned ?? 0));
	const segmentsAnalyzed = $derived(Number(result.segments_analyzed ?? 0));
	const succeeded = $derived(Number(result.succeeded ?? 0));
	const failed = $derived(Number(result.failed ?? 0));
	const skipped = $derived(Number(result.skipped ?? 0));
</script>

<div class="audio-result">
	<div class="stat-grid compact">
		{#if trackCount > 0}
			<div class="stat-card mini">
				<h4>Tracks</h4>
				<p class="stat-value">{trackCount}</p>
			</div>
		{/if}
		{#if segmentsPlanned > 0 || segmentsCreated > 0}
			<div class="stat-card mini">
				<h4>Segments</h4>
				<p class="stat-value">{segmentsCreated || segmentsAnalyzed}/{segmentsPlanned || '—'}</p>
			</div>
		{/if}
		{#if succeeded > 0 || failed > 0 || skipped > 0}
			<div class="stat-card mini">
				<h4>Items</h4>
				<p class="stat-value">✓{succeeded} · ✗{failed} · ⊘{skipped}</p>
			</div>
		{/if}
	</div>
	{#if result.analysis_decision}
		<p class="muted">Decision: <code>{String(result.analysis_decision)}</code></p>
	{/if}
	{#if result.analysis_mode}
		<p class="muted">Mode: {String(result.analysis_mode)}</p>
	{/if}
	{#if status === 'partial'}
		<p class="muted warn">Job completed with partial success.</p>
	{/if}
</div>

<style>
	.audio-result .stat-grid.compact {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-sm);
		margin-bottom: var(--space-sm);
	}
	.stat-card.mini {
		padding: var(--space-sm);
		min-width: 5rem;
	}
	.stat-card.mini h4 {
		margin: 0 0 0.15rem;
		font-size: 0.75rem;
		color: var(--color-muted);
		font-weight: 500;
	}
	.stat-card.mini .stat-value {
		margin: 0;
		font-size: 1rem;
	}
	.warn {
		color: var(--color-warning);
	}
</style>
