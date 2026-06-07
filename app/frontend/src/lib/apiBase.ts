const DEFAULT_API_ORIGIN = 'http://127.0.0.1:8765';

export const API_ORIGIN: string =
	(typeof import.meta.env.VITE_API_BASE_URL === 'string' &&
		import.meta.env.VITE_API_BASE_URL.trim()) ||
	DEFAULT_API_ORIGIN;

export const API_V1 = `${API_ORIGIN.replace(/\/$/, '')}/api/v1`;

export function isCoreUnreachableError(message: string): boolean {
	const lower = message.toLowerCase();
	return (
		lower.includes('failed to fetch') ||
		lower.includes('networkerror') ||
		lower.includes('fetch failed') ||
		lower.includes('impossible de joindre') ||
		lower.includes('cannot reach the core')
	);
}

export function coreOfflineMessage(): string {
	return `Cannot reach the core at ${API_ORIGIN}. Make sure Docker is running.`;
}
