<script lang="ts">
	import type { AdvancedCoverage, FeatureCoverage } from '$lib/featuresApi';
	import StatusBadge from '$lib/components/common/StatusBadge.svelte';

	type Props = {
		coverage: FeatureCoverage | null;
		advancedCoverage: AdvancedCoverage | null;
		modelsReady?: boolean;
		loading?: boolean;
		error?: string | null;
	};

	let {
		coverage,
		advancedCoverage,
		modelsReady = false,
		loading = false,
		error = null
	}: Props = $props();

	const trackCount = $derived(coverage?.summary.track_count ?? advancedCoverage?.summary.track_count ?? 0);
	const withLowlevel = $derived(coverage?.summary.with_essentia_lowlevel ?? 0);
	const withTf = $derived(advancedCoverage?.summary.with_any_advanced_features ?? 0);
	const withEmbeddings = $derived(advancedCoverage?.summary.with_embeddings ?? 0);

	const pct = (n: number) => (trackCount > 0 ? ((n / trackCount) * 100).toFixed(1) : '0.0');
</script>

{#if loading}
	<p class="muted">Loading local coverage…</p>
{:else if error}
	<p class="error">{error}</p>
{:else}
	<div class="stat-grid">
		<div class="stat-card">
			<h3>Essentia low-level</h3>
			<p class="stat-value">{pct(withLowlevel)}%</p>
			<p class="muted">{withLowlevel.toLocaleString()} / {trackCount.toLocaleString()} tracks</p>
		</div>
		<div class="stat-card">
			<h3>TensorFlow features</h3>
			<p class="stat-value">{pct(withTf)}%</p>
			<p class="muted">{withTf.toLocaleString()} tracks with TF data</p>
		</div>
		<div class="stat-card">
			<h3>Embeddings</h3>
			<p class="stat-value">{pct(withEmbeddings)}%</p>
			<p class="muted">{withEmbeddings.toLocaleString()} tracks</p>
		</div>
		<div class="stat-card">
			<h3>Models</h3>
			<p class="stat-value">
				<StatusBadge
					variant={modelsReady ? 'idle' : 'warning'}
					label={modelsReady ? 'Ready' : 'Not ready'}
				/>
			</p>
			<p class="muted">Real TensorFlow inference</p>
		</div>
	</div>
{/if}

<style>
	.stat-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
		gap: var(--space-md);
		margin-bottom: var(--space-lg);
	}
	.stat-card h3 {
		margin: 0 0 0.25rem;
		font-size: 0.9rem;
	}
	.stat-value {
		font-size: 1.5rem;
		font-weight: 600;
		margin: 0;
	}
</style>
