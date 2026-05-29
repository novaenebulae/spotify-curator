<script lang="ts">
	import type { DiffResult, SnapshotMeta } from '$lib/spotifyApi';

	type Props = {
		snapshots: SnapshotMeta[];
		loading?: boolean;
		busy?: boolean;
		error?: string | null;
		diff: DiffResult | null;
		diffLoading?: boolean;
		diffError?: string | null;
		fromId: string;
		toId: string;
		onFromChange: (id: string) => void;
		onToChange: (id: string) => void;
		onRefresh: () => void;
		onCreate: (type: 'full' | 'liked' | 'playlists') => void;
		onCompare: () => void;
	};

	let {
		snapshots,
		loading = false,
		busy = false,
		error = null,
		diff,
		diffLoading = false,
		diffError = null,
		fromId,
		toId,
		onFromChange,
		onToChange,
		onRefresh,
		onCreate,
		onCompare
	}: Props = $props();

	const latestLiked = $derived(
		snapshots.find((s) => s.type === 'liked' || s.type === 'full') ?? null
	);
	const latestPlaylists = $derived(
		snapshots.find((s) => s.type === 'playlists' || s.type === 'full') ?? null
	);
</script>

<section class="card">
	<h2>Snapshots</h2>
	<p class="muted">Create dated backups and compare two snapshots.</p>

	<div class="row actions">
		<button type="button" onclick={() => onCreate('full')} disabled={busy}>Create full snapshot</button>
		<button type="button" class="secondary" onclick={() => onCreate('liked')} disabled={busy}>
			Liked only
		</button>
		<button type="button" class="secondary" onclick={() => onCreate('playlists')} disabled={busy}>
			Playlists only
		</button>
		<button type="button" class="secondary" onclick={onRefresh} disabled={loading || busy}>
			Refresh list
		</button>
	</div>

	<div class="highlights">
		<div>
			<h3>Latest liked-related</h3>
			{#if latestLiked}
				<p><code>{latestLiked.id.slice(0, 12)}…</code> — {latestLiked.created_at}</p>
				<p class="muted">{latestLiked.track_count} tracks</p>
			{:else}
				<p class="muted">None yet</p>
			{/if}
		</div>
		<div>
			<h3>Latest playlists-related</h3>
			{#if latestPlaylists}
				<p><code>{latestPlaylists.id.slice(0, 12)}…</code> — {latestPlaylists.created_at}</p>
				<p class="muted">{latestPlaylists.playlist_count} playlists</p>
			{:else}
				<p class="muted">None yet</p>
			{/if}
		</div>
	</div>

	{#if loading}
		<p class="muted">Loading snapshots…</p>
	{:else if snapshots.length === 0}
		<p class="muted">No snapshots yet. Create one after importing your library.</p>
	{:else}
		<table>
			<thead>
				<tr>
					<th>Created</th>
					<th>Type</th>
					<th>Tracks</th>
					<th>Playlists</th>
					<th>ID</th>
				</tr>
			</thead>
			<tbody>
				{#each snapshots as snap}
					<tr>
						<td>{snap.created_at}</td>
						<td>{snap.type}</td>
						<td>{snap.track_count}</td>
						<td>{snap.playlist_count}</td>
						<td><code>{snap.id.slice(0, 10)}…</code></td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}

	{#if error}
		<pre class="error">{error}</pre>
	{/if}

	<h3>Compare snapshots</h3>
	<div class="row compare">
		<label>
			From
			<select value={fromId} onchange={(e) => onFromChange((e.currentTarget as HTMLSelectElement).value)}>
				<option value="">Select…</option>
				{#each snapshots as snap}
					<option value={snap.id}>{snap.created_at} ({snap.type})</option>
				{/each}
			</select>
		</label>
		<label>
			To
			<select value={toId} onchange={(e) => onToChange((e.currentTarget as HTMLSelectElement).value)}>
				<option value="">Select…</option>
				{#each snapshots as snap}
					<option value={snap.id}>{snap.created_at} ({snap.type})</option>
				{/each}
			</select>
		</label>
		<button type="button" onclick={onCompare} disabled={!fromId || !toId || busy || diffLoading}>
			{diffLoading ? 'Comparing…' : 'Compare'}
		</button>
	</div>

	{#if diffError}
		<pre class="error">{diffError}</pre>
	{/if}

	{#if diff}
		<div class="diff-summary">
			<h3>Diff summary</h3>
			<ul>
				<li>Liked added: {diff.summary.liked.added_count}</li>
				<li>Liked removed: {diff.summary.liked.removed_count}</li>
				<li>Playlists added: {diff.summary.playlists.added_count}</li>
				<li>Playlists removed: {diff.summary.playlists.removed_count}</li>
				<li>Playlists changed: {diff.summary.playlists.changed_count}</li>
			</ul>
			{#if Object.keys(diff.summary.track_status_counts).length > 0}
				<p>Track statuses:</p>
				<ul>
					{#each Object.entries(diff.summary.track_status_counts) as [status, count]}
						<li><code>{status}</code>: {count}</li>
					{/each}
				</ul>
			{/if}
			<details>
				<summary>Full diff JSON</summary>
				<pre>{JSON.stringify(diff, null, 2)}</pre>
			</details>
		</div>
	{/if}
</section>
