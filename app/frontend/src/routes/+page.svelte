<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { fetchHealth } from '$lib/coreApi';
	import { fetchLibrarySummary } from '$lib/libraryApi';
	import { fetchAuthStatus } from '$lib/spotifyApi';

	let loading = $state(true);
	let offline = $state(false);
	let coreOk = $state(false);
	let coreVersion = $state('—');
	let spotifyConnected = $state(false);
	let tracksTotal = $state(0);
	let playlistsTotal = $state(0);
	let latestSnapshot: { id: string; created_at?: string } | null = $state(null);

	onMount(async () => {
		loading = true;
		offline = false;
		try {
			const [health, summary, auth] = await Promise.all([
				fetchHealth(),
				fetchLibrarySummary(),
				fetchAuthStatus()
			]);
			coreOk = health.status === 'ok';
			coreVersion = health.version ?? '—';
			tracksTotal = summary.tracks_total;
			playlistsTotal = summary.playlists_total;
			latestSnapshot = summary.latest_snapshot;
			spotifyConnected = auth.connected || summary.spotify_connected;
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
			<p class="stat-value" style="font-size: 1rem">
				{latestSnapshot ? latestSnapshot.id.slice(0, 8) + '…' : 'None'}
			</p>
			{#if latestSnapshot?.created_at}
				<p class="muted">{latestSnapshot.created_at.slice(0, 10)}</p>
			{/if}
		</div>
	</div>

	<section class="card">
		<h2>Quick actions</h2>
		<div class="row actions">
			<button type="button" onclick={() => goto('/library')}>Open Library</button>
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
			<p>Browse {tracksTotal.toLocaleString()} tracks, review duplicates, and run dry-run actions.</p>
			<button type="button" onclick={() => goto('/library')}>Open Library</button>
		{/if}
	</section>
{/if}
