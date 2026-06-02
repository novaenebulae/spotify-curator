import { get, writable } from 'svelte/store';

import { previewStreamUrl } from '$lib/previewApi';

/** Reactive play state for preview buttons. */
export const activePreviewTrackId = writable<number | null>(null);

let audioEl: HTMLAudioElement | null = null;

export function getActivePreviewTrackId(): number | null {
	return get(activePreviewTrackId);
}

export function stopPreview(): void {
	if (audioEl) {
		audioEl.pause();
		audioEl.src = '';
	}
	activePreviewTrackId.set(null);
}

export async function playPreview(trackId: number): Promise<void> {
	const url = previewStreamUrl(trackId);
	if (!audioEl) {
		audioEl = new Audio();
	}
	const active = get(activePreviewTrackId);
	if (active === trackId && audioEl && !audioEl.paused) {
		audioEl.pause();
		activePreviewTrackId.set(null);
		return;
	}
	stopPreview();
	audioEl.src = url;
	activePreviewTrackId.set(trackId);
	try {
		await audioEl.play();
	} catch (e) {
		activePreviewTrackId.set(null);
		throw e;
	}
}
