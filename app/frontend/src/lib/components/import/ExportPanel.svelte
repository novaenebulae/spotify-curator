<script lang="ts">
	import {
		exportDiffJson,
		exportLikedTracks,
		exportPlaylists,
		exportSnapshotJson,
		type ExportResult
	} from '$lib/spotifyApi';

	type ExportTarget = 'liked_tracks' | 'playlists' | 'latest_snapshot' | 'snapshot_diff';
	type ExportFormat = 'csv' | 'json';

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

	let exportTarget: ExportTarget = $state('liked_tracks');
	let exportFormat: ExportFormat = $state('csv');
	let exportMessage: string | null = $state(null);
	let exportError: string | null = $state(null);
	let exporting = $state(false);
	let lastResult: ExportResult | null = $state(null);

	const formatOptions = $derived(
		exportTarget === 'liked_tracks' || exportTarget === 'playlists'
			? (['csv', 'json'] as ExportFormat[])
			: (['json'] as ExportFormat[])
	);

	$effect(() => {
		if (!formatOptions.includes(exportFormat)) {
			exportFormat = 'json';
		}
	});

	async function runExport(): Promise<void> {
		exporting = true;
		exportError = null;
		exportMessage = null;
		lastResult = null;
		try {
			let res: ExportResult;
			if (exportTarget === 'liked_tracks') {
				res = await exportLikedTracks(exportFormat);
			} else if (exportTarget === 'playlists') {
				res = await exportPlaylists(exportFormat);
			} else if (exportTarget === 'latest_snapshot') {
				if (!latestSnapshotId) throw new Error('No snapshot available to export.');
				res = await exportSnapshotJson(latestSnapshotId);
			} else {
				if (!fromSnapshotId || !toSnapshotId) {
					throw new Error('Select two snapshots to export a diff.');
				}
				res = await exportDiffJson(fromSnapshotId, toSnapshotId);
			}
			lastResult = res;
			exportMessage = `Export completed: ${res.filename}`;
		} catch (e) {
			exportError = e instanceof Error ? e.message : String(e);
		} finally {
			exporting = false;
		}
	}
</script>

<section class="card export-panel">
	<h2>Export</h2>
	<p class="muted">Files are written to the local <code>exports/</code> directory inside Docker.</p>

	<div class="field-row">
		<label>
			Export target
			<select class="select" bind:value={exportTarget}>
				<option value="liked_tracks">Liked tracks</option>
				<option value="playlists">Playlists</option>
				<option value="latest_snapshot">Latest snapshot</option>
				<option value="snapshot_diff">Snapshot diff</option>
			</select>
		</label>
		<label>
			Format
			<select class="select" bind:value={exportFormat}>
				{#each formatOptions as fmt}
					<option value={fmt}>{fmt.toUpperCase()}</option>
				{/each}
			</select>
		</label>
		<button type="button" disabled={busy || exporting} onclick={runExport} style="align-self: end;">Export</button>
	</div>

	{#if exporting}
		<p class="muted">Writing export file…</p>
	{/if}
	{#if lastResult}
		<div class="card" style="margin-top: 1rem; background: var(--color-surface-elevated)">
			<p><strong>{lastResult.filename}</strong></p>
			<p class="muted">{lastResult.row_count} row(s)</p>
			<p class="muted"><code>{lastResult.path}</code></p>
		</div>
	{/if}
	{#if exportMessage && !lastResult}
		<p class="ok">{exportMessage}</p>
	{/if}
	{#if exportError}
		<pre class="error">{exportError}</pre>
	{/if}
</section>
