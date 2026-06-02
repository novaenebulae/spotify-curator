<script lang="ts">
	import AlbumCover from '$lib/components/common/AlbumCover.svelte';
	import TrackPreviewButton from '$lib/components/library/TrackPreviewButton.svelte';
	import StatusBadge from '$lib/components/common/StatusBadge.svelte';
	import type { TrackItem } from '$lib/libraryApi';
	import { formatDuration } from '$lib/libraryApi';

	let {
		items,
		selectedIds,
		sortField,
		sortOrder,
		onToggle,
		onTogglePage,
		onSort,
		onInspect
	}: {
		items: TrackItem[];
		selectedIds: Set<number>;
		sortField: string;
		sortOrder: string;
		onToggle: (id: number) => void;
		onTogglePage: (checked: boolean) => void;
		onSort: (field: string) => void;
		onInspect?: (track: TrackItem) => void;
	} = $props();

	const pageAllSelected = $derived(
		items.length > 0 && items.every((t) => selectedIds.has(t.track_id))
	);

	function sortLabel(field: string, label: string): string {
		if (sortField !== field) return label;
		return `${label} ${sortOrder === 'asc' ? '↑' : '↓'}`;
	}

	function spotifyHref(track: TrackItem): string | null {
		return track.external_url || (track.spotify_uri ? track.spotify_uri.replace('spotify:', 'https://open.spotify.com/') : null);
	}

	function isUnavailable(track: TrackItem): boolean {
		const s = track.availability_status || track.market_status;
		return s !== 'available' && s !== 'unknown';
	}
</script>

<div class="table-sticky-wrap table-sticky library-table-wrap">
	<table class="library-table">
		<colgroup>
			<col class="col-check" />
			<col class="col-cover" />
			<col class="col-preview" />
			<col class="col-track" />
			<col class="col-duration" />
			<col class="col-liked" />
			<col class="col-playlists" />
			<col class="col-isrc" />
			<col class="col-status" />
		</colgroup>
		<thead>
			<tr>
				<th class="col-check">
					<input
						type="checkbox"
						checked={pageAllSelected}
						onchange={(e) => onTogglePage((e.currentTarget as HTMLInputElement).checked)}
					/>
				</th>
				<th class="col-cover">Cover</th>
				<th class="col-preview">Preview</th>
				<th
					><button type="button" class="sort-btn" onclick={() => onSort('title')}
						>{sortLabel('title', 'Track')}</button
					></th
				>
				<th
					><button type="button" class="sort-btn" onclick={() => onSort('duration_ms')}
						>{sortLabel('duration_ms', 'Duration')}</button
					></th
				>
				<th
					><button type="button" class="sort-btn" onclick={() => onSort('liked_added_at')}
						>{sortLabel('liked_added_at', 'Liked')}</button
					></th
				>
				<th class="col-playlists">Pl.</th>
				<th class="col-isrc">ISRC</th>
				<th class="col-status">Status</th>
			</tr>
		</thead>
		<tbody>
			{#each items as track (track.track_id)}
				<tr>
					<td>
						<input
							type="checkbox"
							checked={selectedIds.has(track.track_id)}
							onchange={() => onToggle(track.track_id)}
						/>
					</td>
					<td>
						<AlbumCover
							src={track.album?.cover_image_url}
							alt={track.album?.name ?? track.title}
							size="md"
							href={spotifyHref(track)}
						/>
					</td>
					<td class="col-preview">
						<div class="preview-cell">
							<TrackPreviewButton trackId={track.track_id} />
						</div>
					</td>
					<td class="col-track">
						<div class="track-cell">
							<div class="track-cell-meta">
								<div class="track-primary-line">
									<p class="track-cell-title">
										{#if onInspect}
											<button
												type="button"
												class="title-inspect"
												onclick={() => onInspect(track)}
											>
												{track.title}
											</button>
										{:else if spotifyHref(track)}
											<a href={spotifyHref(track)} target="_blank" rel="noopener noreferrer"
												>{track.title}</a
											>
										{:else}
											{track.title}
										{/if}
										{#if onInspect && spotifyHref(track)}
											<a
												class="spotify-link"
												href={spotifyHref(track)}
												target="_blank"
												rel="noopener noreferrer"
												aria-label="Open in Spotify"
												onclick={(e) => e.stopPropagation()}
											>
												↗
											</a>
										{/if}
									</p>
									<p class="track-cell-artists">{track.artist_names.join(', ')}</p>
								</div>
								{#if track.album?.name}
									<p class="track-cell-sub track-cell-album">{track.album.name}</p>
								{/if}
								<div class="track-badges">
									{#if track.liked}
										<StatusBadge variant="liked" label="Liked" />
									{/if}
									{#if isUnavailable(track)}
										<StatusBadge variant="unavailable" label="Unavailable" />
									{/if}
									{#if track.duplicate_status && track.duplicate_status !== 'none'}
										<StatusBadge variant="duplicate" label={track.duplicate_status} />
									{/if}
								</div>
							</div>
						</div>
					</td>
					<td class="col-duration">{formatDuration(track.duration_ms)}</td>
					<td class="col-liked liked-date"
						>{track.liked_added_at ? track.liked_added_at.slice(0, 10) : '—'}</td
					>
					<td>{track.playlist_count}</td>
					<td><code>{track.isrc ?? '—'}</code></td>
					<td>{track.availability_status}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.library-table {
		table-layout: fixed;
		width: 100%;
	}
	.library-table .col-check {
		width: 2.5rem;
	}
	.library-table .col-cover {
		width: 3.5rem;
	}
	.library-table .col-preview {
		width: 3.25rem;
	}
	.library-table .col-track {
		width: auto;
		min-width: 280px;
	}
	.library-table .col-duration {
		width: 4.5rem;
	}
	.library-table .col-liked {
		width: 6.75rem;
	}
	.library-table .col-playlists {
		width: 2.75rem;
	}
	.library-table .col-isrc {
		width: 8.5rem;
	}
	.library-table .col-status {
		width: 5.5rem;
	}
	.col-preview {
		text-align: center;
	}
	.preview-cell {
		display: flex;
		justify-content: center;
		align-items: center;
	}
	.liked-date {
		white-space: nowrap;
		font-variant-numeric: tabular-nums;
	}
	.track-primary-line {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.35rem 0.75rem;
	}
	.track-cell-title {
		margin: 0;
		font-weight: 600;
		min-width: 0;
	}
	.track-cell-artists {
		margin: 0;
		font-size: 0.85rem;
		color: var(--color-muted);
		flex: 1 1 8rem;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.track-cell-album {
		margin: 0.15rem 0 0;
	}
	.track-badges {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
		margin-top: 0.25rem;
	}
	.sort-btn {
		background: none;
		border: none;
		color: inherit;
		padding: 0;
		font: inherit;
		cursor: pointer;
	}
	.title-inspect {
		background: none;
		border: none;
		color: var(--color-accent, #1db954);
		padding: 0;
		font: inherit;
		font-weight: 600;
		cursor: pointer;
		text-align: left;
		text-decoration: underline;
		text-underline-offset: 2px;
	}
	.spotify-link {
		margin-left: 0.35rem;
		font-size: 0.85rem;
		color: var(--color-muted);
		text-decoration: none;
	}
	.spotify-link:hover {
		color: var(--color-text);
	}
</style>
