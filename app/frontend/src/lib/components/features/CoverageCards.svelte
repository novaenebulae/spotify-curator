<script lang="ts">
	import type { AdvancedCoverage, FeatureCoverage } from '$lib/featuresApi';

	type Props = {
		coverage: FeatureCoverage | null;
		advancedCoverage?: AdvancedCoverage | null;
		loading?: boolean;
	};

	let { coverage, advancedCoverage = null, loading = false }: Props = $props();

	const trackCount = $derived(coverage?.summary.track_count ?? 0);
	const rbPct = $derived(coverage?.summary.coverage_percent ?? 0);
	const rbMissing = $derived(coverage?.summary.missing_reccobeats ?? 0);
	const withLowlevel = $derived(coverage?.summary.with_essentia_lowlevel ?? 0);
	const withTf = $derived(advancedCoverage?.summary.with_any_advanced_features ?? 0);
	const localPct = $derived(trackCount > 0 ? (withTf / trackCount) * 100 : 0);
	const localMissing = $derived(
		trackCount > 0 ? Math.max(0, trackCount - withTf) : 0
	);
</script>

{#if loading && !coverage}
	<p class="muted">Loading coverage…</p>
{:else if coverage}
	<div class="stat-grid">
		<div class="stat-card">
			<h3>Total tracks</h3>
			<p class="stat-value">{trackCount.toLocaleString()}</p>
		</div>
		<div class="stat-card">
			<h3>ReccoBeats coverage</h3>
			<p class="stat-value">{rbPct.toFixed(1)}%</p>
			<p class="muted">{coverage.summary.with_reccobeats.toLocaleString()} enriched</p>
		</div>
		<div class="stat-card">
			<h3>ReccoBeats missing</h3>
			<p class="stat-value">{rbMissing.toLocaleString()}</p>
		</div>
		<div class="stat-card">
			<h3>Local analysis coverage</h3>
			<p class="stat-value">{localPct.toFixed(1)}%</p>
			<p class="muted">
				{withLowlevel.toLocaleString()} low-level · {withTf.toLocaleString()} with TensorFlow
			</p>
		</div>
		<div class="stat-card">
			<h3>Local analysis missing</h3>
			<p class="stat-value">{localMissing.toLocaleString()}</p>
		</div>
	</div>
{:else}
	<p class="muted">No coverage data yet.</p>
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
