<script lang="ts">
	import type { FeatureCoverage } from '$lib/featuresApi';

	type Props = {
		coverage: FeatureCoverage | null;
		loading?: boolean;
	};

	let { coverage, loading = false }: Props = $props();
</script>

{#if loading}
	<p class="muted">Loading coverage…</p>
{:else if coverage}
	<div class="stat-grid">
		<div class="stat-card">
			<h3>Total tracks</h3>
			<p class="stat-value">{coverage.summary.track_count.toLocaleString()}</p>
		</div>
		<div class="stat-card">
			<h3>ReccoBeats coverage</h3>
			<p class="stat-value">{coverage.summary.coverage_percent.toFixed(1)}%</p>
			<p class="muted">{coverage.summary.with_reccobeats.toLocaleString()} enriched</p>
		</div>
		<div class="stat-card">
			<h3>ReccoBeats missing</h3>
			<p class="stat-value">{coverage.summary.missing_reccobeats.toLocaleString()}</p>
		</div>

		{#each coverage.sources.filter((s) => s.source === 'essentia_lowlevel') as src}
			<div class="stat-card">
				<h3>Essentia coverage</h3>
				<p class="stat-value">{src.coverage_percent.toFixed(1)}%</p>
				<p class="muted">{(coverage.summary.with_essentia_lowlevel ?? 0).toLocaleString()} enriched</p>
			</div>
			<div class="stat-card">
				<h3>Essentia missing</h3>
				<p class="stat-value">{(coverage.summary.missing_essentia_lowlevel ?? 0).toLocaleString()}</p>
			</div>
		{/each}
	</div>
{:else}
	<p class="muted">No coverage data yet.</p>
{/if}
