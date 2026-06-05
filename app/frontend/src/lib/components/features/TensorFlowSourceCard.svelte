<script lang="ts">
	import GenreDiscogs519Block from '$lib/components/features/GenreDiscogs519Block.svelte';
	import type { TrackFeatureSource } from '$lib/featuresApi';
	import type { AdvancedGenre, AdvancedScalarFeature } from '$lib/featuresApi';

	const GENRE_SCALAR_NAMES = new Set([
		'genre_discogs_519',
		'genre_discogs_519_top_label',
		'genre_discogs_519_top_score',
		'genre_discogs_519_top_k'
	]);

	type Props = {
		source: TrackFeatureSource;
	};

	let { source }: Props = $props();

	const scalars = $derived(
		((source.extended?.scalar_features as AdvancedScalarFeature[] | undefined) ?? []).filter(
			(f) => !GENRE_SCALAR_NAMES.has(f.feature_name)
		)
	);
	const genre = $derived((source.extended?.genre as AdvancedGenre | undefined) ?? null);

	function formatScalarValue(f: AdvancedScalarFeature): string {
		if (f.value == null) return '—';
		if (typeof f.value === 'number') {
			if (f.value >= 0 && f.value <= 1) return f.value.toFixed(3);
			return String(f.value);
		}
		return String(f.value);
	}
</script>

<article class="source-card">
	<GenreDiscogs519Block
		{genre}
		sourceLabel={source.display_name}
		sourceStatus={source.status}
	/>

	{#if scalars.length > 0}
		<h4 class="scalars-title">Classifier features</h4>
		<div class="metric-grid">
			{#each scalars as f (f.feature_name)}
				<div class="metric">
					<span class="name">{f.feature_name.replace(/_/g, ' ')}</span>
					<span class="value">{formatScalarValue(f)}</span>
					{#if f.confidence != null}
						<span class="muted">conf {f.confidence.toFixed(2)}</span>
					{/if}
					{#if f.missing_reason}
						<span class="warn">{f.missing_reason}</span>
					{/if}
				</div>
			{/each}
		</div>
	{:else if !genre?.top_k?.length}
		<p class="muted">No TensorFlow scalar features stored.</p>
	{/if}
</article>

<style>
	.source-card {
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		padding: var(--space-md);
		margin-bottom: var(--space-md);
	}
	.source-card :global(.genre-block) {
		border: none;
		padding: 0;
		margin-bottom: var(--space-md);
	}
	.scalars-title {
		margin: 0 0 0.5rem;
		font-size: 0.95rem;
	}
	.metric-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
		gap: var(--space-sm);
	}
	.metric {
		padding: 0.4rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		font-size: 0.85rem;
	}
	.metric .name {
		display: block;
		font-weight: 600;
	}
	.metric .value {
		font-size: 1rem;
	}
	.warn {
		color: var(--color-warn, #ca8);
		font-size: 0.75rem;
	}
</style>
