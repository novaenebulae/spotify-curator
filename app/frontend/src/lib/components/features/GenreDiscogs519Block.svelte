<script lang="ts">
	import StatusBadge from '$lib/components/common/StatusBadge.svelte';
	import type { AdvancedGenre } from '$lib/featuresApi';

	type Props = {
		genre: AdvancedGenre | null;
		/** When set, shows a source header (e.g. Essentia TensorFlow + status). */
		sourceLabel?: string | null;
		sourceStatus?: string | null;
	};

	let { genre, sourceLabel = null, sourceStatus = null }: Props = $props();

	const topGenres = $derived(genre?.top_k?.slice(0, 3) ?? []);

	function genreMessage(g: AdvancedGenre | null): string | null {
		if (!g || topGenres.length > 0) return null;
		if (g.missing_reason === 'AUDIO_TOO_SHORT') {
			return 'Segment too short for MAEST (need ~30s). Rebuild audio-downloader with 30s padding.';
		}
		if (g.missing_reason === 'MODEL_NOT_ON_DISK' || g.missing_reason === 'MODEL_MISSING') {
			return 'Genre model missing or not downloaded.';
		}
		if (g.status === 'model_missing') return 'Genre unavailable (model missing).';
		return 'Genre unavailable (no prediction).';
	}
</script>

<article class="genre-block">
	{#if sourceLabel}
		<header>
			<h3>{sourceLabel}</h3>
			{#if sourceStatus}
				<StatusBadge variant="idle" label={sourceStatus} />
			{/if}
		</header>
	{/if}

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
</article>

<style>
	.genre-block {
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
		font-size: 1rem;
	}
	.genre-top {
		padding: var(--space-sm);
		background: var(--color-surface-elevated);
		border-radius: var(--radius-sm);
	}
	.genre-top h4 {
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
	.muted {
		color: var(--color-muted);
	}
</style>
