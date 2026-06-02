<script lang="ts">
	import type { TrackFeatureSource } from '$lib/featuresApi';
	import FeatureMetricGrid from '$lib/components/features/FeatureMetricGrid.svelte';
	import { formatAnalysisDecision, formatConfidence } from '$lib/featureFormat';

	let { source }: { source: TrackFeatureSource } = $props();

	const hasExtended = $derived(
		source.extended &&
			typeof source.extended === 'object' &&
			Object.keys(source.extended).length > 0
	);
</script>

<article class="source-card" class:inactive={!source.is_active}>
	<header>
		<h3>{source.display_name}</h3>
		<div class="badges">
			{#if source.is_active}
				<span class="badge active">Active</span>
			{:else}
				<span class="badge inactive">Inactive</span>
			{/if}
			<span class="badge status">{source.status}</span>
		</div>
	</header>
	{#if source.feature_confidence != null}
		<p class="conf">{formatConfidence(source.feature_confidence)}</p>
	{/if}
	{#if source.status === 'failed' || source.status === 'not_found'}
		<p class="error">{source.error_message ?? source.error_code ?? 'Analysis failed'}</p>
	{:else if Object.keys(source.fields).length > 0}
		<FeatureMetricGrid fields={source.fields} />
	{:else}
		<p class="muted">No scalar features stored for this source.</p>
	{/if}
	{#if source.pipeline_version}
		<p class="meta">Pipeline: {source.pipeline_version}</p>
	{/if}
	{#if hasExtended}
		<details class="extended">
			<summary>Spectral & timbre (local)</summary>
			<dl class="extended-grid">
				{#if source.extended.segments_used != null}
					<div><dt>Segments</dt><dd>{source.extended.segments_used}</dd></div>
				{/if}
				{#if source.extended.analysis_decision}
					<div>
						<dt>Strategy</dt>
						<dd>{formatAnalysisDecision(String(source.extended.analysis_decision))}</dd>
					</div>
				{/if}
				{#if source.extended.spectral_centroid != null}
					<div><dt>Spectral centroid</dt><dd>{source.extended.spectral_centroid}</dd></div>
				{/if}
				{#if source.extended.spectral_rolloff != null}
					<div><dt>Spectral rolloff</dt><dd>{source.extended.spectral_rolloff}</dd></div>
				{/if}
				{#if source.extended.dynamic_complexity != null}
					<div><dt>Dynamic complexity</dt><dd>{source.extended.dynamic_complexity}</dd></div>
				{/if}
				{#if source.extended.onset_rate != null}
					<div><dt>Onset rate</dt><dd>{source.extended.onset_rate}</dd></div>
				{/if}
			</dl>
		</details>
	{/if}
</article>

<style>
	.source-card {
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		padding: var(--space-md);
		margin-bottom: var(--space-md);
		background: var(--color-surface-elevated);
	}
	.source-card.inactive {
		opacity: 0.85;
	}
	header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-sm);
		margin-bottom: var(--space-sm);
	}
	header h3 {
		margin: 0;
		font-size: 1rem;
	}
	.badges {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
	}
	.badge {
		font-size: 0.7rem;
		padding: 0.1rem 0.4rem;
		border-radius: var(--radius-sm);
		background: var(--color-border);
	}
	.badge.active {
		background: rgba(29, 185, 84, 0.25);
		color: var(--color-success);
	}
	.conf {
		font-size: 0.85rem;
		color: var(--color-muted);
		margin: 0 0 var(--space-sm);
	}
	.error {
		color: var(--color-danger);
		font-size: 0.9rem;
	}
	.meta {
		font-size: 0.8rem;
		color: var(--color-muted);
	}
	.muted {
		color: var(--color-muted);
		font-size: 0.9rem;
	}
	.extended {
		margin-top: var(--space-md);
		font-size: 0.85rem;
	}
	.extended-grid {
		display: grid;
		gap: var(--space-xs);
		margin: var(--space-sm) 0 0;
	}
	.extended-grid dt {
		color: var(--color-muted);
		font-size: 0.75rem;
	}
	.extended-grid dd {
		margin: 0 0 var(--space-xs);
	}
</style>
