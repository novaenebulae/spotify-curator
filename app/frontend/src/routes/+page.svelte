<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { fetchHealth } from '$lib/coreApi';
	import { fetchLibrarySummary } from '$lib/libraryApi';
	import { fetchAuthStatus } from '$lib/spotifyApi';
	import { getFeatureCoverage } from '$lib/featuresApi';
	import { fetchPreviewCoverage, type PreviewCoverage } from '$lib/previewApi';
	import type { FeatureCoverage } from '$lib/featuresApi';

	let loading = $state(true);
	let offline = $state(false);
	let coreOk = $state(false);
	let coreVersion = $state('—');
	let spotifyConnected = $state(false);
	let tracksTotal = $state(0);
	let playlistsTotal = $state(0);
	let latestSnapshot: { id: string; created_at?: string } | null = $state(null);
	let coverage = $state<FeatureCoverage | null>(null);
	let previewCoverage = $state<PreviewCoverage | null>(null);

	const reccobeatsPct = $derived(
		coverage && coverage.summary.track_count > 0
			? Math.round(
					(coverage.summary.with_reccobeats / coverage.summary.track_count) * 1000
				) / 10
			: null
	);

	const essentiaPct = $derived(
		coverage && coverage.summary.track_count > 0
			? Math.round(
					((coverage.summary.with_essentia_lowlevel ?? 0) / coverage.summary.track_count) *
						1000
				) / 10
			: null
	);

	onMount(async () => {
		loading = true;
		offline = false;
		try {
			const [health, summary, auth, cov, previews] = await Promise.all([
				fetchHealth(),
				fetchLibrarySummary(),
				fetchAuthStatus(),
				getFeatureCoverage({ include_failed: false, include_fields: false }).catch(() => null),
				fetchPreviewCoverage().catch(() => null)
			]);
			coreOk = health.status === 'ok';
			coreVersion = health.version ?? '—';
			tracksTotal = summary.tracks_total;
			playlistsTotal = summary.playlists_total;
			latestSnapshot = summary.latest_snapshot;
			spotifyConnected = auth.connected || summary.spotify_connected;
			coverage = cov;
			previewCoverage = previews;
		} catch {
			offline = true;
		} finally {
			loading = false;
		}
	});
</script>

<div class="page-header">
	<h1>Spotify Library Curator</h1>
	<p class="muted">
		Local desktop app to back up, explore, and curate your Spotify library with snapshots,
		duplicates detection, and dry-run actions.
	</p>
</div>

{#if offline}
	<div class="error">Cannot reach the core API. Start Docker with <code>docker compose up</code>.</div>
{:else if loading}
	<p class="muted">Loading dashboard…</p>
{:else}
	<div class="stat-grid">
		<div class="stat-card">
			<h3>Core API</h3>
			<p class="stat-value" class:ok={coreOk} class:status={!coreOk}>{coreOk ? 'Online' : 'Offline'}</p>
			<p class="muted">v{coreVersion}</p>
		</div>
		<div class="stat-card">
			<h3>Spotify</h3>
			<p class="stat-value" class:ok={spotifyConnected}>{spotifyConnected ? 'Connected' : 'Disconnected'}</p>
		</div>
		<div class="stat-card">
			<h3>Tracks imported</h3>
			<p class="stat-value">{tracksTotal.toLocaleString()}</p>
		</div>
		<div class="stat-card">
			<h3>Playlists imported</h3>
			<p class="stat-value">{playlistsTotal.toLocaleString()}</p>
		</div>
		<div class="stat-card">
			<h3>Latest snapshot</h3>
			<p class="stat-value snapshot-id">
				{latestSnapshot ? latestSnapshot.id.slice(0, 8) + '…' : 'None'}
			</p>
			{#if latestSnapshot?.created_at}
				<p class="muted">{latestSnapshot.created_at.slice(0, 10)}</p>
			{/if}
		</div>
	</div>

	{#if tracksTotal > 0}
		<h2 class="section-label">Enrichment &amp; audio</h2>
		<div class="stat-grid enrichment-grid">
			<button type="button" class="stat-card stat-card-link" onclick={() => goto('/features')}>
				<h3>ReccoBeats</h3>
				{#if reccobeatsPct != null}
					<p class="stat-value">{reccobeatsPct}%</p>
					<p class="muted">
						{coverage?.summary.with_reccobeats.toLocaleString() ?? '—'} / {tracksTotal.toLocaleString()}
						tracks
					</p>
				{:else}
					<p class="stat-value muted">—</p>
					<p class="muted">Open Features</p>
				{/if}
			</button>
			<button type="button" class="stat-card stat-card-link" onclick={() => goto('/features')}>
				<h3>Essentia (local)</h3>
				{#if essentiaPct != null}
					<p class="stat-value">{essentiaPct}%</p>
					<p class="muted">
						{(coverage?.summary.with_essentia_lowlevel ?? 0).toLocaleString()} analyzed
					</p>
				{:else}
					<p class="stat-value muted">—</p>
					<p class="muted">Segments + analysis</p>
				{/if}
			</button>
			<button type="button" class="stat-card stat-card-link" onclick={() => goto('/library')}>
				<h3>Deezer previews</h3>
				{#if previewCoverage}
					<p class="stat-value">{previewCoverage.coverage_percent}%</p>
					<p class="muted">
						{previewCoverage.with_deezer_preview.toLocaleString()} / {previewCoverage.track_count.toLocaleString()}
					</p>
				{:else}
					<p class="stat-value muted">—</p>
					<p class="muted">Resolve from Library</p>
				{/if}
			</button>
			<button type="button" class="stat-card stat-card-link" onclick={() => goto('/features')}>
				<h3>Feature enrichment</h3>
				<p class="stat-value link-label">Open →</p>
				<p class="muted">Jobs, coverage, failures, local analysis</p>
			</button>
		</div>
	{/if}

	<section class="card">
		<h2>Quick actions</h2>
		<div class="row actions">
			<button type="button" onclick={() => goto('/library')}>Open Library</button>
			<button type="button" class="secondary" onclick={() => goto('/features')}>Features</button>
			<button type="button" class="secondary" onclick={() => goto('/import')}>Import Library</button>
			<button type="button" class="secondary" onclick={() => goto('/settings')}>Settings</button>
		</div>
	</section>

	<section class="card">
		<h2>Next steps</h2>
		{#if tracksTotal === 0}
			<p>Import your liked tracks and playlists to get started.</p>
			<button type="button" onclick={() => goto('/import')}>Go to Import</button>
		{:else}
			<p>Browse {tracksTotal.toLocaleString()} tracks, enrich features, resolve previews, and run dry-run actions.</p>
			<div class="row actions">
				<button type="button" onclick={() => goto('/library')}>Open Library</button>
				<button type="button" class="secondary" onclick={() => goto('/features')}>Enrich features</button>
			</div>
		{/if}
	</section>
{/if}

<style>
	.section-label {
		font-size: 1rem;
		font-weight: 600;
		margin: var(--space-xl) 0 var(--space-md);
		color: var(--color-muted);
	}
	.enrichment-grid {
		margin-top: 0;
	}
	.stat-card-link {
		text-align: left;
		cursor: pointer;
		width: 100%;
		font: inherit;
		color: inherit;
		transition:
			border-color 0.15s,
			background 0.15s;
	}
	.stat-card-link:hover {
		border-color: var(--color-accent);
		background: var(--color-surface-elevated);
	}
	.stat-card-link .stat-value {
		color: var(--color-accent);
	}
	.link-label {
		font-size: 1.25rem !important;
	}
	.snapshot-id {
		font-size: 1rem;
	}
	.ok {
		color: var(--color-success);
	}
</style>
