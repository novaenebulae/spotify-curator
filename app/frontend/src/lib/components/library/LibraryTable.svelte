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
		onSort
	}: {
		items: TrackItem[];
		selectedIds: Set<number>;
		sortField: string;
		sortOrder: string;
		onToggle: (id: number) => void;
		onTogglePage: (checked: boolean) => void;
		onSort: (field: string) => void;
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

<div class="table-sticky-wrap table-sticky">
	<table>
		<thead>
			<tr>
				<th>
					<input
						type="checkbox"
						checked={pageAllSelected}
						onchange={(e) => onTogglePage((e.currentTarget as HTMLInputElement).checked)}
					/>
				</th>
				<th>Cover</th>
				<th>Preview</th>
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
				<th>Playlists</th>
				<th>ISRC</th>
				<th>Status</th>
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
					<td>
						<TrackPreviewButton trackId={track.track_id} />
					</td>
					<td>
						<div class="track-cell">
							<div class="track-cell-meta">
								<p class="track-cell-title">
									{#if spotifyHref(track)}
										<a href={spotifyHref(track)} target="_blank" rel="noopener noreferrer"
											>{track.title}</a
										>
									{:else}
										{track.title}
									{/if}
								</p>
								<p class="track-cell-sub">{track.artist_names.join(', ')}</p>
								{#if track.album?.name}
									<p class="track-cell-sub">{track.album.name}</p>
								{/if}
								<div class="row" style="margin-top: 0.25rem; gap: 0.35rem">
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
					<td>{formatDuration(track.duration_ms)}</td>
					<td>{track.liked_added_at ? track.liked_added_at.slice(0, 10) : '—'}</td>
					<td>{track.playlist_count}</td>
					<td><code>{track.isrc ?? '—'}</code></td>
					<td>{track.availability_status}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.sort-btn {
		background: none;
		border: none;
		color: inherit;
		padding: 0;
		font: inherit;
		cursor: pointer;
	}
</style>
