<script lang="ts">
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
</script>

<div class="table-wrap">
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
				<th
					><button type="button" class="sort-btn" onclick={() => onSort('title')}
						>{sortLabel('title', 'Title')}</button
					></th
				>
				<th>Artists</th>
				<th
					><button type="button" class="sort-btn" onclick={() => onSort('album')}
						>{sortLabel('album', 'Album')}</button
					></th
				>
				<th
					><button type="button" class="sort-btn" onclick={() => onSort('duration_ms')}
						>{sortLabel('duration_ms', 'Duration')}</button
					></th
				>
				<th
					><button type="button" class="sort-btn" onclick={() => onSort('liked_added_at')}
						>{sortLabel('liked_added_at', 'Liked added')}</button
					></th
				>
				<th>Playlists</th>
				<th>ISRC</th>
				<th>Availability</th>
				<th>Duplicate</th>
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
					<td>{track.title}</td>
					<td>{track.artist_names.join(', ')}</td>
					<td>{track.album?.name ?? '—'}</td>
					<td>{formatDuration(track.duration_ms)}</td>
					<td>{track.liked_added_at ? track.liked_added_at.slice(0, 10) : '—'}</td>
					<td>{track.playlist_count}</td>
					<td><code>{track.isrc ?? '—'}</code></td>
					<td>{track.availability_status}</td>
					<td>{track.duplicate_status}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.table-wrap {
		overflow-x: auto;
	}
	.sort-btn {
		background: none;
		border: none;
		color: inherit;
		padding: 0;
		font: inherit;
		cursor: pointer;
	}
</style>
