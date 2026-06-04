<script lang="ts">
	import StatusBadge from '$lib/components/common/StatusBadge.svelte';
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
	const topGenres = $derived(genre?.top_k?.slice(0, 3) ?? []);

	function formatScalarValue(f: AdvancedScalarFeature): string {
		if (f.value == null) return '—';
		if (typeof f.value === 'number') {
			if (f.value >= 0 && f.value <= 1) return f.value.toFixed(3);
			return String(f.value);
		}
		return String(f.value);
	}

	function genreMessage(g: AdvancedGenre | null): string | null {
		if (!g || topGenres.length > 0) return null;
		if (g.missing_reason === 'AUDIO_TOO_SHORT') {
			return 'Segment too short for MAEST (need ~30s). Rebuild audio-downloader with 30s padding.';
		}
		if (g.missing_reason === 'MODEL_NOT_ON_DISK') {
			return 'Genre model missing or not downloaded.';
		}
		if (g.missing_reason === 'MODEL_MISSING') return 'Genre model missing or not downloaded.';
		if (g.status === 'model_missing') return 'Genre unavailable (model missing).';
		return 'Genre unavailable (no prediction).';
	}
</script>

<article class="source-card">
	<header>
		<h3>{source.display_name}</h3>
		<StatusBadge variant="idle" label={source.status} />
	</header>

	{#if topGenres.length > 0}
		<div class="genre-top">
			<h4>Top 3 genres (Discogs519)</h4>
			<ol>
				{#each topGenres as item, i}
					<li>
						<span class="rank">{i + 1}.</span>
						<strong>{item.label ?? '—'}</strong>
						<span class="muted">
							{item.score != null ? item.score.toFixed(3) : '—'}
						</span>
					</li>
				{/each}
			</ol>
		</div>
	{:else if genre}
		<div class="genre-top">
			<h4>Genre (Discogs519)</h4>
			<p class="muted">{genreMessage(genre)}</p>
		</div>
	{/if}

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
	{:else if topGenres.length === 0}
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
	header {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		margin-bottom: var(--space-sm);
	}
	header h3 {
		margin: 0;
	}
	.genre-top {
		margin-bottom: var(--space-md);
		padding: var(--space-sm);
		background: var(--color-surface-elevated);
		border-radius: var(--radius-sm);
	}
	.genre-top h4,
	.scalars-title {
		margin: 0 0 0.5rem;
		font-size: 0.95rem;
	}
	.genre-top ol {
		margin: 0;
		padding-left: 1.25rem;
	}
	.genre-top li {
		margin-bottom: 0.25rem;
	}
	.rank {
		margin-right: 0.35rem;
		color: var(--color-muted);
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
