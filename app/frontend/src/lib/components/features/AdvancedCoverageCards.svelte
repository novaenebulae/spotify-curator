<script lang="ts">
	import type { AdvancedCoverage } from '$lib/featuresApi';
	import StatusBadge from '$lib/components/common/StatusBadge.svelte';

	type Props = {
		coverage: AdvancedCoverage | null;
		loading?: boolean;
		error?: string | null;
	};

	let { coverage, loading = false, error = null }: Props = $props();

	const pctAdvanced = $derived(
		coverage && coverage.summary.track_count > 0
			? (coverage.summary.with_any_advanced_features / coverage.summary.track_count) * 100
			: 0
	);

	const pctEmbeddings = $derived(
		coverage && coverage.summary.track_count > 0
			? (coverage.summary.with_embeddings / coverage.summary.track_count) * 100
			: 0
	);
</script>

{#if loading}
	<p class="muted">Loading TensorFlow coverage…</p>
{:else if error}
	<p class="error">{error}</p>
{:else if coverage}
	<div class="stat-grid">
		<div class="stat-card">
			<h3>Advanced features</h3>
			<p class="stat-value">{pctAdvanced.toFixed(1)}%</p>
			<p class="muted">
				{coverage.summary.with_any_advanced_features.toLocaleString()} / {coverage.summary.track_count.toLocaleString()}
			</p>
		</div>
		<div class="stat-card">
			<h3>Embeddings</h3>
			<p class="stat-value">{pctEmbeddings.toFixed(1)}%</p>
			<p class="muted">{coverage.embeddings.tracks_with_embedding.toLocaleString()} tracks</p>
		</div>
		<div class="stat-card">
			<h3>Real inference</h3>
			<p class="stat-value">
				<StatusBadge
					variant={coverage.models_summary.real_inference_ready ? 'idle' : 'warning'}
					label={coverage.models_summary.real_inference_ready ? 'Ready' : 'Not ready'}
				/>
			</p>
			<p class="muted">Profile: {coverage.models_summary.default_profile}</p>
		</div>
		{#if coverage.models_summary.missing_model_keys.length > 0}
			<div class="stat-card wide">
				<h3>Missing models</h3>
				<p class="muted missing-list">
					{coverage.models_summary.missing_model_keys.slice(0, 8).join(', ')}
					{#if coverage.models_summary.missing_model_keys.length > 8}
						… (+{coverage.models_summary.missing_model_keys.length - 8})
					{/if}
				</p>
			</div>
		{/if}
	</div>
{:else}
	<p class="muted">No advanced coverage data yet.</p>
{/if}

<style>
	.stat-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
		gap: var(--space-md);
		margin-bottom: var(--space-lg);
	}
	.stat-card.wide {
		grid-column: 1 / -1;
	}
	.missing-list {
		font-size: 0.85rem;
		word-break: break-word;
	}
</style>
