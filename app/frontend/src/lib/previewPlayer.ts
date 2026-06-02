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
	// #region agent log
	fetch('http://127.0.0.1:7620/ingest/6a9de88f-eb8b-4142-bcaa-afef6d0d7d9b', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '8df333' },
		body: JSON.stringify({
			sessionId: '8df333',
			runId: 'post-fix',
			hypothesisId: 'H2',
			location: 'previewPlayer.ts:playPreview',
			message: 'play via proxy',
			data: { trackId, urlHost: new URL(url).host },
			timestamp: Date.now()
		})
	}).catch(() => {});
	// #endregion
	try {
		await audioEl.play();
	} catch (e) {
		activePreviewTrackId.set(null);
		throw e;
	}
}
