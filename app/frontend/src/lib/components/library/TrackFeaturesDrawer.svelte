<script lang="ts">
	import { onDestroy } from 'svelte';
	import AlbumCover from '$lib/components/common/AlbumCover.svelte';
	import FeatureMetricGrid from '$lib/components/features/FeatureMetricGrid.svelte';
	import SourceFeatureCard from '$lib/components/features/SourceFeatureCard.svelte';
	import TrackFeaturesAdvancedPanel from '$lib/components/features/TrackFeaturesAdvancedPanel.svelte';
	import {
		formatAnalysisDecision,
		formatConfidence
	} from '$lib/featureFormat';
	import { getTrackFeatures, type TrackFeaturesResponse } from '$lib/featuresApi';
	import { getTrackPreview, type TrackPreview } from '$lib/previewApi';
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

	let tab: 'fusion' | 'sources' | 'advanced' = $state('fusion');
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
		if (!data?.merged) return 'Not analysed';
		if (data.merged.status === 'success') return 'Analysed';
		if (data.merged.status === 'partial') return 'Partial';
		return data.merged.status;
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

	const hasEssentiaSource = $derived(
		data?.sources.some((s) => s.source_name === 'essentia_lowlevel') ?? false
	);
	const sortedSources = $derived(
		data?.sources
			? [...data.sources].sort((a, b) => {
					if (a.source_name === 'essentia_lowlevel') return -1;
					if (b.source_name === 'essentia_lowlevel') return 1;
					return a.source_name.localeCompare(b.source_name);
				})
			: []
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
			tab = 'fusion';
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
				class:active={tab === 'fusion'}
				onclick={() => (tab = 'fusion')}
			>
				Fusion
			</button>
			<button
				type="button"
				class:active={tab === 'sources'}
				onclick={() => (tab = 'sources')}
			>
				Sources
			</button>
			<button
				type="button"
				class:active={tab === 'advanced'}
				onclick={() => (tab = 'advanced')}
			>
				Advanced
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
					<p class="hint">
						Then verify:
						<code>curl http://127.0.0.1:8765/api/v1/features/tracks/1</code>
					</p>
				</div>
			{:else if error}
				<p class="error">{error}</p>
			{:else if tab === 'fusion'}
				{#if !data?.merged}
					<p class="muted">No analysis results yet.</p>
					<p class="hint">
						Run ReccoBeats enrichment or local analysis from the <a href="/features">Features</a>
						page.
					</p>
				{:else}
					<p class="primary-source">
						Primary source: <strong>{data.merged.display_name}</strong>
						{#if !data.merged.is_active}
							<span class="muted"> (inactive row)</span>
						{/if}
					</p>
					{#if data.sources.length > 1}
						<p class="hint-banner">
							{#if data.merged.primary_source === 'essentia_lowlevel'}
								Mood metrics (energy, valence) are on the ReccoBeats card in Sources.
							{:else}
								Local timbre details may be on the Essentia card in Sources.
							{/if}
						</p>
					{/if}
					{#if data.merged.feature_confidence != null}
						<p class="conf">{formatConfidence(data.merged.feature_confidence)}</p>
					{/if}
					{#if data.merged.status === 'failed'}
						<p class="error">{data.merged.error_message ?? data.merged.error_code}</p>
					{:else if Object.keys(data.merged.fields).length > 0}
						<FeatureMetricGrid fields={data.merged.fields} />
					{/if}
					{#if data.merged.meta.analysis_decision}
						<p class="meta">
							Analysis strategy: {formatAnalysisDecision(data.merged.meta.analysis_decision)}
						</p>
					{/if}
					{#if data.merged.meta.segments_used != null}
						<p class="meta">{data.merged.meta.segments_used} segment(s) analysed</p>
					{/if}
					{#if data.merged.meta.pipeline_version}
						<p class="meta">Pipeline: {data.merged.meta.pipeline_version}</p>
					{/if}
				{/if}
			{:else if tab === 'advanced' && track}
				<TrackFeaturesAdvancedPanel
					{data}
					trackId={track.track_id}
					{loading}
					error={null}
					{offline}
				/>
			{:else if data}
				{#if data.sources.length === 0}
					<p class="muted">No source data stored for this track.</p>
				{:else}
					{#if !hasEssentiaSource}
						<p class="hint-banner">
							No local Essentia low-level analysis for this track yet. Run
							<a href="/features">Download then analyze</a> on the Features page, then reopen this
							drawer.
						</p>
					{/if}
					{#each sortedSources as source (source.source_name)}
						<SourceFeatureCard {source} />
					{/each}
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
	.primary-source {
		margin-top: 0;
	}
	.hint-banner {
		font-size: 0.85rem;
		color: var(--color-muted);
		background: var(--color-surface-elevated);
		padding: var(--space-sm);
		border-radius: var(--radius-sm);
	}
	.conf,
	.meta,
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
	.stale-api-banner .hint {
		font-size: 0.85rem;
		margin: var(--space-sm) 0 0;
	}
</style>
