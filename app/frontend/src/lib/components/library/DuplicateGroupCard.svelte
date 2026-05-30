<script lang="ts">
	import AlbumCover from '$lib/components/common/AlbumCover.svelte';
	import type { DuplicateGroup } from '$lib/libraryApi';
	import { formatDuration } from '$lib/libraryApi';

	let { group }: { group: DuplicateGroup } = $props();

	function spotifyHref(track: DuplicateGroup['tracks'][0]): string | null {
		return (
			track.external_url ||
			(track.spotify_uri
				? track.spotify_uri.replace('spotify:', 'https://open.spotify.com/')
				: null) ||
			null
		);
	}
</script>

<article class="card dup-group-card">
	<header class="dup-group-header">
		<h3>{group.reason_label}</h3>
		<p class="muted">
			{#if group.isrc}
				ISRC: <code>{group.isrc}</code> ·
			{/if}
			{group.occurrence_count} occurrence(s) · {group.unique_track_count} unique track(s) · confidence
			{group.confidence.toFixed(2)}
		</p>
	</header>

	{#if group.is_repeated_occurrence}
		<p class="dup-warning">
			Repeated occurrence — the same track appears multiple times in the library. Review contexts
			before treating this as a duplicate to remove.
		</p>
	{:else if group.unique_track_count > 1}
		<p class="muted">
			{group.unique_track_count} distinct tracks share this duplicate signal — review before bulk
			actions.
		</p>
	{/if}

	{#each group.tracks as track (track.track_id)}
		<div class="dup-track-card">
			<AlbumCover
				src={track.cover_image_url}
				alt={track.album_name ?? track.title}
				size="xl"
				href={spotifyHref(track)}
			/>
			<div>
				<p class="track-cell-title">
					{#if spotifyHref(track)}
						<a href={spotifyHref(track)} target="_blank" rel="noopener noreferrer">{track.title}</a>
					{:else}
						{track.title}
					{/if}
					{#if track.occurrence_count && track.occurrence_count > 1}
						<span class="muted"> ×{track.occurrence_count}</span>
					{/if}
				</p>
				<p class="track-cell-sub">{track.artist_names.join(', ')}</p>
				{#if track.album_name}
					<p class="track-cell-sub">{track.album_name}</p>
				{/if}
				<p class="muted">
					{#if track.duration_ms}
						{formatDuration(track.duration_ms)} ·
					{/if}
					{#if track.spotify_track_id}
						<code>{track.spotify_track_id}</code>
					{/if}
				</p>
				{#if track.contexts && track.contexts.length > 0}
					<p class="muted">
						Playlists:
						{track.contexts.map((c) => c.name).join(', ')}
					</p>
				{/if}
				{#if spotifyHref(track)}
					<p><a href={spotifyHref(track)} target="_blank" rel="noopener noreferrer">Open in Spotify</a></p>
				{/if}
			</div>
		</div>
	{/each}
</article>
