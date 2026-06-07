<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import AlbumCover from '$lib/components/common/AlbumCover.svelte';
	import DryRunModal from '$lib/components/library/DryRunModal.svelte';
	import DuplicateGroupCard from '$lib/components/library/DuplicateGroupCard.svelte';
	import LibraryTable from '$lib/components/library/LibraryTable.svelte';
	import TrackFeaturesDrawer from '$lib/components/library/TrackFeaturesDrawer.svelte';
	import { fetchPreviewCoverage, resolveDeezerPreviews, type PreviewCoverage } from '$lib/previewApi';
	import { hydrateLastJobsFromApi, trackJob } from '$lib/jobTracker';
	import {
		dryRunAction,
		fetchDuplicates,
		fetchLibraryActionDetail,
		fetchLibraryActions,
		fetchMissingTracks,
		fetchTracks,
		type DryRunResponse,
		type DuplicateGroup,
		type LibraryActionSummary,
		type MissingItem,
		type TrackItem,
		type TrackQuery
	} from '$lib/libraryApi';

	type Tab = 'tracks' | 'duplicates' | 'missing' | 'history';

	let tab: Tab = $state('tracks');
	let loading = $state(true);
	let error: string | null = $state(null);
	let offline = $state(false);

	let items: TrackItem[] = $state([]);
	let total = $state(0);
	let totalPages = $state(0);
	let page = $state(1);
	let pageSize = $state(50);
	let sortField = $state('liked_added_at');
	let sortOrder = $state('desc');

	let q = $state('');
	let likedFilter = $state('');
	let duplicateFilter = $state('');
	let selectedIds: Set<number> = $state(new Set());

	let duplicateGroups: DuplicateGroup[] = $state([]);
	let duplicateSummary = $state({ group_count: 0, track_count: 0 });
	let missingItems: MissingItem[] = $state([]);
	let missingSummary: Record<string, number> = $state({});
	let historyItems: LibraryActionSummary[] = $state([]);
	let historyDetail: Record<string, unknown> | null = $state(null);

	let dryRunOpen = $state(false);
	let dryRunResult: DryRunResponse | null = $state(null);
	let dryRunLabel = $state('');
	let actionBusy = $state(false);
	let tracksRefreshing = $state(false);
	let inspectTrack: TrackItem | null = $state(null);
	let previewCoverage = $state<PreviewCoverage | null>(null);
	let previewCoverageError = $state<string | null>(null);
	let previewBusy = $state(false);

	const controller = new AbortController();
	let tracksFetchController: AbortController | null = null;

	function libraryPerfEnabled(): boolean {
		return (
			import.meta.env.DEV &&
			typeof localStorage !== 'undefined' &&
			localStorage.getItem('LIBRARY_PERF_LOG') === '1'
		);
	}

	async function loadTracks(): Promise<void> {
		tracksFetchController?.abort();
		const fetchAc = new AbortController();
		tracksFetchController = fetchAc;
		const hadItems = items.length > 0;
		if (!hadItems) loading = true;
		else tracksRefreshing = true;
		error = null;
		offline = false;
		const perfMark = libraryPerfEnabled() ? `library-tracks-${Date.now()}` : null;
		if (perfMark) performance.mark(`${perfMark}-start`);
		try {
			const query: TrackQuery = {
				page,
				page_size: pageSize,
				sort: sortField,
				order: sortOrder
			};
			if (q.trim()) query.q = q.trim();
			if (likedFilter === 'true') query.liked = true;
			if (likedFilter === 'false') query.liked = false;
			if (duplicateFilter) query.duplicate_status = duplicateFilter;

			const res = await fetchTracks(query, fetchAc.signal);
			if (fetchAc.signal.aborted) return;
			items = res.items;
			total = res.pagination.total;
			totalPages = res.pagination.total_pages;
			if (perfMark) {
				performance.mark(`${perfMark}-end`);
				performance.measure('library-tracks', `${perfMark}-start`, `${perfMark}-end`);
				const m = performance.getEntriesByName('library-tracks').at(-1);
				if (m) console.debug('[library perf] tracks render ms', Math.round(m.duration));
			}
		} catch (e) {
			if (fetchAc.signal.aborted) return;
			const msg = e instanceof Error ? e.message : String(e);
			offline =
				msg.toLowerCase().includes('cannot reach the core') ||
				msg.toLowerCase().includes('impossible de joindre');
			error = msg;
			if (!hadItems) items = [];
		} finally {
			if (!fetchAc.signal.aborted) {
				loading = false;
				tracksRefreshing = false;
			}
		}
	}

	async function loadDuplicates(): Promise<void> {
		loading = true;
		error = null;
		try {
			const res = await fetchDuplicates({ strategy: 'all', page_size: 20 }, controller.signal);
			duplicateGroups = res.groups;
			duplicateSummary = res.summary;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	async function loadMissing(): Promise<void> {
		loading = true;
		error = null;
		try {
			const res = await fetchMissingTracks({ page_size: 50 }, controller.signal);
			missingItems = res.items;
			missingSummary = res.summary;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	async function loadHistory(): Promise<void> {
		loading = true;
		error = null;
		try {
			const res = await fetchLibraryActions({ dry_run: true }, controller.signal);
			historyItems = res.items;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	async function refresh(): Promise<void> {
		selectedIds = new Set();
		if (tab === 'tracks') await loadTracks();
		else if (tab === 'duplicates') await loadDuplicates();
		else if (tab === 'missing') await loadMissing();
		else await loadHistory();
	}

	async function loadPreviewCoverage(): Promise<void> {
		previewCoverageError = null;
		try {
			previewCoverage = await fetchPreviewCoverage();
		} catch (e) {
			previewCoverageError = e instanceof Error ? e.message : String(e);
		}
	}

	async function resolvePreviews(): Promise<void> {
		previewBusy = true;
		previewCoverageError = null;
		try {
			const { job_id } = await resolveDeezerPreviews({ only_missing: true });
			await trackJob(job_id, 'Resolve Deezer previews', {
				onComplete: async () => {
					await hydrateLastJobsFromApi();
					await loadPreviewCoverage();
				}
			});
		} catch (e) {
			previewCoverageError = e instanceof Error ? e.message : String(e);
		} finally {
			previewBusy = false;
		}
	}

	function toggleSelect(id: number): void {
		const next = new Set(selectedIds);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selectedIds = next;
	}

	function togglePage(checked: boolean): void {
		if (!checked) {
			selectedIds = new Set();
			return;
		}
		selectedIds = new Set(items.map((t) => t.track_id));
	}

	function onSort(field: string): void {
		if (sortField === field) sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		else {
			sortField = field;
			sortOrder = 'asc';
		}
		page = 1;
		loadTracks();
	}

	async function runDryRun(actionType: string, label: string): Promise<void> {
		if (selectedIds.size === 0) {
			error = 'Select at least one track.';
			return;
		}
		actionBusy = true;
		error = null;
		try {
			const body: Parameters<typeof dryRunAction>[0] = {
				action_type: actionType,
				track_ids: [...selectedIds]
			};
			if (actionType === 'create_backup_playlist') {
				body.options = { backup_playlist_name: `Backup ${new Date().toISOString().slice(0, 10)}` };
			}
			dryRunResult = await dryRunAction(body, controller.signal);
			dryRunLabel = label;
			dryRunOpen = true;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			actionBusy = false;
		}
	}

	async function showHistoryDetail(id: number): Promise<void> {
		try {
			historyDetail = await fetchLibraryActionDetail(id, controller.signal);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	}

	function switchTab(next: Tab): void {
		inspectTrack = null;
		tab = next;
		refresh();
	}

	function closeFeaturesDrawer(): void {
		inspectTrack = null;
	}

	onMount(() => {
		loadTracks();
		loadPreviewCoverage();
	});

	onDestroy(() => {
		tracksFetchController?.abort();
		controller.abort();
	});
</script>

<div class="page-header">
	<h1>Library management</h1>
	<p class="muted">Browse, filter, and prepare dry-run actions on your imported tracks.</p>
</div>

	<div class="row tabs">
		<div class="tabs-left">
			<button type="button" class:secondary={tab !== 'tracks'} onclick={() => switchTab('tracks')}
				>Tracks</button
			>
			<button
				type="button"
				class:secondary={tab !== 'duplicates'}
				onclick={() => switchTab('duplicates')}>Duplicates</button
			>
			<button type="button" class:secondary={tab !== 'missing'} onclick={() => switchTab('missing')}
				>Missing</button
			>
			<button type="button" class:secondary={tab !== 'history'} onclick={() => switchTab('history')}
				>History</button
			>
			<button type="button" class="secondary" onclick={refresh} disabled={loading}>Refresh</button>
		</div>
		<div class="tabs-right">
			{#if previewCoverage}
				<button type="button" class="preview-btn" disabled={previewBusy} onclick={resolvePreviews}>
					<span class="preview-btn-title">Resolve Deezer previews</span>
					<span class="preview-btn-sub">
						{previewCoverage.with_deezer_preview} / {previewCoverage.track_count}
						({previewCoverage.coverage_percent}%)
					</span>
				</button>
			{:else if previewCoverageError}
				<span class="muted">{previewCoverageError}</span>
			{/if}
		</div>
	</div>

	{#if offline}
		<div class="error">Core offline — start Docker (`docker compose up`).</div>
	{:else if error}
		<div class="error">{error}</div>
	{/if}

	{#if tab === 'tracks'}
		<section class="card">
			<div class="search-row">
				<input
					class="search-input"
					type="search"
					placeholder="Search title, artist, album, ISRC…"
					bind:value={q}
					onkeydown={(e) => {
						if (e.key === 'Enter') {
							page = 1;
							loadTracks();
						}
					}}
				/>
			</div>
			<div class="row filters-row">
				<select
					bind:value={likedFilter}
					onchange={() => {
						page = 1;
						loadTracks();
					}}
				>
					<option value="">Liked — all</option>
					<option value="true">Liked — yes</option>
					<option value="false">Liked — no</option>
				</select>
				<select
					bind:value={duplicateFilter}
					onchange={() => {
						page = 1;
						loadTracks();
					}}
				>
					<option value="">Duplicates — all</option>
					<option value="potential">Potential duplicates</option>
					<option value="confirmed">Confirmed duplicates</option>
				</select>
				<button
					type="button"
					onclick={() => {
						page = 1;
						loadTracks();
					}}>Search</button
				>
			</div>
			<p class="muted">
				{total} result(s) — {selectedIds.size} selected
				{#if tracksRefreshing}<span class="refresh-hint"> (updating…)</span>{/if}
			</p>

			{#if loading && items.length === 0}
				<p class="muted">Loading…</p>
			{:else if items.length === 0}
				<p class="muted">
					No tracks. Import your library from <a href="/import">Import</a>.
				</p>
			{:else}
				<LibraryTable
					{items}
					{selectedIds}
					{sortField}
					{sortOrder}
					onToggle={toggleSelect}
					onTogglePage={togglePage}
					{onSort}
					onInspect={(t) => (inspectTrack = t)}
				/>
			{/if}

			<div class="row actions">
				<button
					type="button"
					class="secondary"
					disabled={page <= 1 || (loading && items.length === 0)}
					onclick={() => {
						inspectTrack = null;
						page -= 1;
						loadTracks();
					}}>←</button
				>
				<span class="muted">Page {page} / {Math.max(totalPages, 1)}</span>
				<button
					type="button"
					class="secondary"
					disabled={page >= totalPages || (loading && items.length === 0)}
					onclick={() => {
						inspectTrack = null;
						page += 1;
						loadTracks();
					}}>→</button
				>
			</div>

			<div class="row actions">
				<button
					type="button"
					disabled={actionBusy || selectedIds.size === 0}
					onclick={() => runDryRun('unlike_tracks', 'Unlike tracks')}>Dry-run unlike</button
				>
				<button
					type="button"
					disabled={actionBusy || selectedIds.size === 0}
					onclick={() => runDryRun('restore_liked_tracks', 'Restore liked')}
					>Dry-run restore</button
				>
				<button
					type="button"
					disabled={actionBusy || selectedIds.size === 0}
					onclick={() => runDryRun('create_backup_playlist', 'Backup playlist')}
					>Dry-run backup</button
				>
			</div>
		</section>
	{:else if tab === 'duplicates'}
		<section class="card">
			{#if loading}
				<p class="muted">Loading…</p>
			{:else if duplicateGroups.length === 0}
				<p class="muted">No duplicate groups detected.</p>
			{:else}
				<p class="muted">
					{duplicateSummary.group_count} group(s), {duplicateSummary.track_count} track(s)
				</p>
				{#each duplicateGroups as group (group.group_id)}
					<DuplicateGroupCard {group} />
				{/each}
			{/if}
		</section>
	{:else if tab === 'missing'}
		<section class="card">
			{#if loading}
				<p class="muted">Loading…</p>
			{:else}
				<div class="summary-badges row">
					{#each Object.entries(missingSummary) as [status, count]}
						<span class="badge">{status}: {count}</span>
					{/each}
				</div>
				{#if missingItems.length === 0}
					<p class="muted">No missing tracks detected (two snapshots required).</p>
				{:else}
					<table>
						<thead>
							<tr
								><th></th><th>Title</th><th>Artists</th><th>Status</th><th>Detected</th></tr
							>
						</thead>
						<tbody>
							{#each missingItems as item (item.spotify_track_id ?? item.track_id)}
								<tr>
									<td>
										<AlbumCover
											src={item.cover_image_url}
											alt={item.album_name ?? item.title ?? 'Track'}
											size="sm"
										/>
									</td>
									<td>{item.title ?? '—'}</td>
									<td>{item.artist_names.join(', ')}</td>
									<td>{item.status}</td>
									<td>{item.detected_at?.slice(0, 10) ?? '—'}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}
			{/if}
		</section>
	{:else}
		<section class="card">
			{#if loading}
				<p class="muted">Loading…</p>
			{:else if historyItems.length === 0}
				<p class="muted">No actions recorded.</p>
			{:else}
				<table>
					<thead>
						<tr><th>ID</th><th>Type</th><th>Count</th><th>Status</th><th>Date</th><th></th></tr>
					</thead>
					<tbody>
						{#each historyItems as row}
							<tr>
								<td>{row.id}</td>
								<td>{row.action_type}</td>
								<td>{row.affected_count}</td>
								<td>{row.status}</td>
								<td>{row.created_at?.slice(0, 19) ?? '—'}</td>
								<td
									><button type="button" class="secondary" onclick={() => showHistoryDetail(row.id)}
										>Details</button
									></td
								>
							</tr>
						{/each}
					</tbody>
				</table>
				{#if historyDetail}
					<pre class="detail-json">{JSON.stringify(historyDetail, null, 2)}</pre>
				{/if}
			{/if}
		</section>
	{/if}

<DryRunModal
	open={dryRunOpen}
	result={dryRunResult}
	actionLabel={dryRunLabel}
	onClose={() => (dryRunOpen = false)}
/>

<TrackFeaturesDrawer
	track={inspectTrack}
	open={inspectTrack !== null}
	navigationTracks={items}
	onNavigate={(t) => (inspectTrack = t)}
	onClose={closeFeaturesDrawer}
/>

<style>
	.tabs {
		margin-bottom: 1.25rem;
		justify-content: space-between;
		align-items: center;
		gap: 0.75rem;
	}
	.tabs-left {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
		align-items: center;
	}
	.tabs-right {
		display: flex;
		justify-content: flex-end;
		align-items: center;
		gap: 0.5rem;
		min-width: 220px;
	}
	.tabs button {
		margin-right: 0.25rem;
	}
	.preview-btn {
		display: inline-flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.1rem;
		padding: 0.45rem 0.6rem;
	}
	.preview-btn-title {
		font-weight: 600;
	}
	.preview-btn-sub {
		font-size: 0.8rem;
		color: rgba(0, 0, 0, 0.72);
	}
	.search-row {
		display: flex;
		width: 100%;
		margin-bottom: 0.75rem;
	}
	.search-input {
		flex: 1;
		width: 100%;
		min-width: 0;
		padding: 0.5rem 0.65rem;
		background: #2a2a2a;
		color: #eee;
		border: 1px solid #444;
		border-radius: 4px;
	}
	.filters-row select {
		padding: 0.4rem 0.6rem;
		background: #2a2a2a;
		color: #eee;
		border: 1px solid #444;
		border-radius: 4px;
		min-width: 180px;
	}
	.badge {
		background: #2a2a2a;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		font-size: 0.85rem;
	}
	.detail-json {
		background: #2a2a2a;
		padding: 0.75rem;
		border-radius: 6px;
		overflow: auto;
		font-size: 0.8rem;
		max-height: 240px;
	}

	.row.actions {
		margin-left: auto;
		margin-right: auto;
		justify-content: center;
	}
</style>
