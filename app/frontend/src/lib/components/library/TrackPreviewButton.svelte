<script lang="ts">
	import { onDestroy } from 'svelte';
	import { getTrackPreview } from '$lib/previewApi';
	import { getActivePreviewTrackId, playPreview, stopPreview } from '$lib/previewPlayer';

	let { trackId }: { trackId: number } = $props();

	let loading = $state(false);
	let available = $state(false);
	let previewUrl = $state<string | null>(null);
	let error = $state<string | null>(null);

	const isPlaying = $derived(getActivePreviewTrackId() === trackId);

	async function loadPreview() {
		loading = true;
		error = null;
		try {
			const p = await getTrackPreview(trackId);
			available = p.is_available && !!p.preview_url;
			previewUrl = p.preview_url;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
			available = false;
		} finally {
			loading = false;
		}
	}

	async function onClick() {
		if (!available || !previewUrl) return;
		try {
			await playPreview(trackId, previewUrl);
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
{:else if available && previewUrl}
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
		font-size: 0.85rem;
		padding: 0.15rem 0.4rem;
		border: none;
		background: transparent;
		cursor: pointer;
	}
	.preview-btn.muted {
		color: var(--muted, #888);
		cursor: default;
	}
</style>
