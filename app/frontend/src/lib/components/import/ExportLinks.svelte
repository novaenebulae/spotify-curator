<script lang="ts">
	import {
		exportDiffJson,
		exportLikedTracks,
		exportPlaylists,
		exportSnapshotJson,
		type ExportResult
	} from '$lib/spotifyApi';

	type Props = {
		busy?: boolean;
		fromSnapshotId?: string;
		toSnapshotId?: string;
		latestSnapshotId?: string;
	};

	let {
		busy = false,
		fromSnapshotId = '',
		toSnapshotId = '',
		latestSnapshotId = ''
	}: Props = $props();

	let exportMessage: string | null = $state(null);
	let exportError: string | null = $state(null);
	let exporting = $state(false);

	async function runExport(
		label: string,
		fn: () => Promise<ExportResult>
	): Promise<void> {
		exporting = true;
		exportError = null;
		exportMessage = null;
		try {
			const res = await fn();
			exportMessage = `${label}: ${res.filename} (${res.row_count} rows) → ${res.path}`;
		} catch (e) {
			exportError = e instanceof Error ? e.message : String(e);
		} finally {
			exporting = false;
		}
	}
</script>

<section class="card">
	<h2>Exports</h2>
	<p class="muted">Files are written to the local <code>exports/</code> directory (mounted from the repo).</p>

	<div class="row actions">
		<button
			type="button"
			disabled={busy || exporting}
			onclick={() => runExport('Liked CSV', () => exportLikedTracks('csv'))}
		>
			Export liked tracks (CSV)
		</button>
		<button
			type="button"
			disabled={busy || exporting}
			onclick={() => runExport('Liked JSON', () => exportLikedTracks('json'))}
		>
			Export liked tracks (JSON)
		</button>
		<button
			type="button"
			disabled={busy || exporting}
			onclick={() => runExport('Playlists CSV', () => exportPlaylists('csv'))}
		>
			Export playlists (CSV)
		</button>
		<button
			type="button"
			disabled={busy || exporting}
			onclick={() => runExport('Playlists JSON', () => exportPlaylists('json'))}
		>
			Export playlists (JSON)
		</button>
		<button
			type="button"
			disabled={busy || exporting || !latestSnapshotId}
			onclick={() => runExport('Snapshot JSON', () => exportSnapshotJson(latestSnapshotId))}
		>
			Export latest snapshot (JSON)
		</button>
		<button
			type="button"
			disabled={busy || exporting || !fromSnapshotId || !toSnapshotId}
			onclick={() => runExport('Diff JSON', () => exportDiffJson(fromSnapshotId, toSnapshotId))}
		>
			Export diff (JSON)
		</button>
	</div>

	{#if exporting}
		<p class="muted">Writing export file…</p>
	{/if}
	{#if exportMessage}
		<p class="ok">{exportMessage}</p>
	{/if}
	{#if exportError}
		<pre class="error">{exportError}</pre>
	{/if}
</section>
