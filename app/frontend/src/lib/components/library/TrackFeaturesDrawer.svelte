<script lang="ts">
	import { onDestroy } from 'svelte';
	import AlbumCover from '$lib/components/common/AlbumCover.svelte';
	import ResolvedFeaturesGrid from '$lib/components/features/ResolvedFeaturesGrid.svelte';
	import SourceFeatureCard from '$lib/components/features/SourceFeatureCard.svelte';
	import TensorFlowSourceCard from '$lib/components/features/TensorFlowSourceCard.svelte';
	import { getTrackFeatures, type TrackFeaturesResponse } from '$lib/featuresApi';
	import { getTrackPreview, type TrackPreview } from '$lib/previewApi';
	import type { AdvancedGenre } from '$lib/featuresApi';
	import type { TrackItem } from '$lib/libraryApi';
	import { formatDuration } from '$lib/libraryApi';

	let {
		track,
		open = true,
		onClose
	}: {
		track: TrackItem | null;
		open?: boolean;
		onClose: () => void;
	} = $props();

	let tab: 'features' | 'sources' = $state('features');
	let loading = $state(false);
	let error = $state<string | null>(null);
	let offline = $state(false);
	let data = $state<TrackFeaturesResponse | null>(null);
	let preview = $state<TrackPreview | null>(null);

	let featuresController: AbortController | null = null;

	function spotifyHref(t: TrackItem): string | null {
		return (
			t.external_url ||
			(t.spotify_uri ? t.spotify_uri.replace('spotify:', 'https://open.spotify.com/') : null)
		);
	}

	function statusBadge(): string {
		if (!data?.merged && !(data?.resolved_features?.length)) return 'Not analysed';
		if (data?.availability.has_essentia_tensorflow) return 'Analysed (local + TF)';
		if (data?.merged?.status === 'success') return 'Analysed';
		if (data?.merged?.status === 'partial') return 'Partial';
		return data?.merged?.status ?? 'Partial';
	}

	function isStaleCoreApiError(msg: string | null): boolean {
		if (!msg) return false;
		const lower = msg.toLowerCase();
		return (
			msg.includes('(404)') &&
			lower.includes('not found') &&
			!lower.includes('track not found')
		);
	}

	const staleCoreApi = $derived(isStaleCoreApiError(error));

	const classicSources = $derived(
		data?.sources.filter((s) => s.source_name !== 'essentia_tensorflow') ?? []
	);
	const tfSource = $derived(
		data?.sources.find((s) => s.source_name === 'essentia_tensorflow') ?? null
	);
	const tfGenre = $derived((tfSource?.extended?.genre as AdvancedGenre | undefined) ?? null);
	const sortedClassicSources = $derived(
		[...classicSources].sort((a, b) => {
			if (a.source_name === 'essentia_lowlevel') return -1;
			if (b.source_name === 'essentia_lowlevel') return 1;
			return a.source_name.localeCompare(b.source_name);
		})
	);

	async function load() {
		if (!track) return;
		featuresController?.abort();
		const ac = new AbortController();
		featuresController = ac;
		loading = true;
		error = null;
		offline = false;
		data = null;
		preview = null;
		try {
			const [feat, prev] = await Promise.all([
				getTrackFeatures(track.track_id, undefined, ac.signal),
				getTrackPreview(track.track_id).catch(() => null)
			]);
			if (ac.signal.aborted) return;
			data = feat;
			preview = prev;
		} catch (e) {
			if (ac.signal.aborted) return;
			const msg = e instanceof Error ? e.message : String(e);
			if (msg.includes('127.0.0.1:8765')) offline = true;
			else error = msg;
		} finally {
			if (!ac.signal.aborted) loading = false;
		}
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
	}

	$effect(() => {
		if (open && track) {
			tab = 'features';
			load();
		}
	});

	onDestroy(() => featuresController?.abort());
</script>

<svelte:window onkeydown={onKeydown} />

{#if open && track}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div class="drawer-backdrop" role="presentation" onclick={onClose}></div>
	<div class="drawer" role="dialog" aria-modal="true" aria-label="Track features">
		<header class="drawer-header">
			<div class="track-head">
				<AlbumCover
					src={track.album?.cover_image_url}
					alt={track.album?.name ?? track.title}
					size="md"
				/>
				<div>
					<h2>
						{#if spotifyHref(track)}
							<a href={spotifyHref(track)} target="_blank" rel="noopener noreferrer"
								>{track.title}</a
							>
						{:else}
							{track.title}
						{/if}
					</h2>
					<p class="sub">{track.artist_names.join(', ')}</p>
					<p class="sub">{formatDuration(track.duration_ms)}</p>
				</div>
			</div>
			<button type="button" class="close-btn" aria-label="Close" onclick={onClose}>×</button>
		</header>

		<div class="badges-row">
			<span class="badge">{statusBadge()}</span>
			{#if data?.availability.has_essentia_tensorflow}
				<span class="badge preview">TensorFlow</span>
			{/if}
			{#if preview?.is_available}
				<span class="badge preview">Deezer preview</span>
			{/if}
		</div>

		<div class="tabs">
			<button
				type="button"
				class:active={tab === 'features'}
				onclick={() => (tab = 'features')}
			>
				Features
			</button>
			<button
				type="button"
				class:active={tab === 'sources'}
				onclick={() => (tab = 'sources')}
			>
				Sources
			</button>
		</div>

		<div class="drawer-body">
			{#if loading}
				<p class="muted">Loading features…</p>
			{:else if offline}
				<p class="error">Core API unreachable. Is Docker running?</p>
			{:else if staleCoreApi}
				<div class="stale-api-banner">
					<p class="error">The core API image is outdated and does not expose track features yet.</p>
					<p class="hint">
						Rebuild and restart the API:
						<code>docker compose up -d --build core-api</code>
					</p>
				</div>
			{:else if error}
				<p class="error">{error}</p>
			{:else if tab === 'features'}
				<ResolvedFeaturesGrid
					features={data?.resolved_features ?? []}
					genre={tfGenre}
					genreSourceLabel={tfSource?.display_name ?? 'Essentia TensorFlow'}
					genreSourceStatus={tfSource?.status ?? null}
					{loading}
				/>
			{:else if data}
				{#if sortedClassicSources.length === 0 && !tfSource}
					<p class="muted">No source data stored for this track.</p>
					<p class="hint"><a href="/features">Run local analysis on Features →</a></p>
				{:else}
					{#each sortedClassicSources as source (source.source_name)}
						<SourceFeatureCard {source} />
					{/each}
					{#if tfSource}
						<TensorFlowSourceCard source={tfSource} />
					{/if}
				{/if}
			{/if}
		</div>
	</div>
{/if}

<style>
	.drawer-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		z-index: 200;
	}
	.drawer {
		position: fixed;
		top: 0;
		right: 0;
		bottom: 0;
		width: min(480px, 100vw);
		background: var(--color-surface);
		border-left: 1px solid var(--color-border);
		z-index: 201;
		display: flex;
		flex-direction: column;
		box-shadow: -4px 0 24px rgba(0, 0, 0, 0.4);
	}
	.drawer-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		padding: var(--space-lg);
		border-bottom: 1px solid var(--color-border);
	}
	.track-head {
		display: flex;
		gap: var(--space-md);
		align-items: flex-start;
	}
	.track-head h2 {
		margin: 0;
		font-size: 1.1rem;
	}
	.sub {
		margin: 0.15rem 0 0;
		font-size: 0.85rem;
		color: var(--color-muted);
	}
	.close-btn {
		background: none;
		border: none;
		color: var(--color-text);
		font-size: 1.5rem;
		cursor: pointer;
		line-height: 1;
		padding: 0 var(--space-sm);
	}
	.badges-row {
		display: flex;
		gap: var(--space-sm);
		padding: var(--space-sm) var(--space-lg);
		flex-wrap: wrap;
	}
	.badge {
		font-size: 0.75rem;
		padding: 0.15rem 0.5rem;
		border-radius: var(--radius-sm);
		background: var(--color-border);
	}
	.badge.preview {
		background: rgba(29, 185, 84, 0.2);
	}
	.tabs {
		display: flex;
		gap: 0;
		border-bottom: 1px solid var(--color-border);
		padding: 0 var(--space-lg);
	}
	.tabs button {
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--color-muted);
		padding: var(--space-sm) var(--space-md);
		cursor: pointer;
		font: inherit;
	}
	.tabs button.active {
		color: var(--color-text);
		border-bottom-color: var(--color-accent);
	}
	.drawer-body {
		flex: 1;
		overflow: auto;
		padding: var(--space-lg);
	}
	.hint {
		font-size: 0.85rem;
		color: var(--color-muted);
	}
	.error {
		color: var(--color-danger);
	}
	.muted {
		color: var(--color-muted);
	}
	.stale-api-banner {
		background: var(--color-surface-elevated);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		padding: var(--space-md);
	}
</style>
