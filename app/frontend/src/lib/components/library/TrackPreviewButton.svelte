<script lang="ts">
	import { onDestroy } from 'svelte';
	import { getTrackPreview } from '$lib/previewApi';
	import {
		activePreviewTrackId,
		getActivePreviewTrackId,
		playPreview,
		stopPreview
	} from '$lib/previewPlayer';

	let { trackId }: { trackId: number } = $props();

	let loading = $state(false);
	let available = $state(false);
	let error = $state<string | null>(null);

	const isPlaying = $derived($activePreviewTrackId === trackId);

	async function loadPreview() {
		loading = true;
		error = null;
		try {
			const p = await getTrackPreview(trackId);
			available = Boolean(p.is_available);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
			available = false;
		} finally {
			loading = false;
		}
	}

	async function onClick() {
		if (!available) return;
		try {
			await playPreview(trackId);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	}

	onDestroy(() => {
		if (getActivePreviewTrackId() === trackId) stopPreview();
	});

	$effect(() => {
		trackId;
		loadPreview();
	});
</script>

{#if loading}
	<span class="preview-btn muted" aria-busy="true">…</span>
{:else if available}
	<button
		type="button"
		class="preview-btn"
		title="Deezer preview (streaming)"
		aria-pressed={isPlaying}
		onclick={onClick}
	>
		{isPlaying ? '⏸' : '▶'}
	</button>
{:else}
	<span class="preview-btn muted" title={error ?? 'Preview unavailable'}>—</span>
{/if}

<style>
	.preview-btn {
		font-size: 1rem;
		line-height: 1;
		min-width: 2rem;
		min-height: 2rem;
		padding: 0.25rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		background: var(--color-surface-elevated);
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}
	.preview-btn:not(.muted):hover {
		border-color: var(--color-accent);
		color: var(--color-accent);
	}
	.preview-btn.muted {
		color: var(--muted, #888);
		cursor: default;
	}
</style>
