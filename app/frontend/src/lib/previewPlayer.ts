let audioEl: HTMLAudioElement | null = null;
let activeTrackId: number | null = null;

export function getActivePreviewTrackId(): number | null {
	return activeTrackId;
}

export function stopPreview(): void {
	if (audioEl) {
		audioEl.pause();
		audioEl.src = '';
	}
	activeTrackId = null;
}

export async function playPreview(trackId: number, url: string): Promise<void> {
	if (!audioEl) {
		audioEl = new Audio();
	}
	if (activeTrackId === trackId && !audioEl.paused) {
		audioEl.pause();
		activeTrackId = null;
		return;
	}
	stopPreview();
	audioEl.src = url;
	activeTrackId = trackId;
	await audioEl.play();
}
