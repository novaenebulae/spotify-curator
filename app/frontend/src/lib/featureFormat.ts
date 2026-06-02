const KEY_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'] as const;

const CAMELOT_MAJOR = [
	'8B',
	'3B',
	'10B',
	'5B',
	'12B',
	'7B',
	'2B',
	'9B',
	'4B',
	'11B',
	'6B',
	'1B'
] as const;
const CAMELOT_MINOR = [
	'5A',
	'12A',
	'7A',
	'2A',
	'9A',
	'4A',
	'11A',
	'6A',
	'1A',
	'8A',
	'3A',
	'10A'
] as const;

export function formatKeyMode(key: number | undefined, mode: number | undefined): string | null {
	if (key === undefined || key === null || mode === undefined || mode === null) return null;
	const name = KEY_NAMES[key % 12] ?? String(key);
	const modeLabel = mode === 1 ? 'major' : 'minor';
	return `${name} ${modeLabel}`;
}

export function formatCamelot(key: number | undefined, mode: number | undefined): string | null {
	if (key === undefined || key === null || mode === undefined || mode === null) return null;
	const table = mode === 1 ? CAMELOT_MAJOR : CAMELOT_MINOR;
	return table[key % 12] ?? null;
}

export function formatPercent(value: number | undefined): string | null {
	if (value === undefined || value === null) return null;
	if (value >= 0 && value <= 1) return `${Math.round(value * 100)}%`;
	return String(value);
}

export function formatBpm(value: number | undefined): string | null {
	if (value === undefined || value === null) return null;
	return `${Math.round(value * 10) / 10} BPM`;
}

export function formatConfidence(value: number | undefined): string | null {
	if (value === undefined || value === null) return null;
	if (value >= 0 && value <= 1) return `${Math.round(value * 100)}% confidence`;
	return String(value);
}

export function formatAnalysisDecision(code: string | undefined): string {
	if (!code) return '';
	return code.replaceAll('_', ' ');
}

export const MOOD_FIELDS = ['energy', 'valence', 'danceability'] as const;
export const TEXTURE_FIELDS = ['acousticness', 'instrumentalness', 'speechiness', 'liveness'] as const;
export const RHYTHM_FIELDS = ['bpm', 'time_signature'] as const;

export const FIELD_LABELS: Record<string, string> = {
	bpm: 'Tempo',
	energy: 'Energy',
	danceability: 'Danceability',
	valence: 'Valence',
	acousticness: 'Acoustic',
	instrumentalness: 'Instrumental',
	speechiness: 'Speech',
	liveness: 'Live',
	loudness: 'Loudness',
	key: 'Key',
	mode: 'Mode',
	time_signature: 'Time signature',
	duration_ms: 'Duration'
};
