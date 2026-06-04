import type { ModelProfileItem } from '$lib/modelsApi';

const PROFILE_TITLES: Record<string, string> = {
	'phase6-minimal': 'Minimal — EffNet + moods',
	'phase6-recommended': 'Recommended — + genre MAEST',
	'phase6-full': 'Full — + arousal / valence (MusicNN)'
};

export function profileDisplayName(profileKey: string): string {
	return PROFILE_TITLES[profileKey] ?? profileKey.replace(/_/g, ' ');
}

export function profileModelsFor(
	profileKey: string,
	allModels: { model_key: string; display_name: string; required_for: string[] }[]
): string[] {
	return allModels
		.filter((m) => m.required_for.includes(profileKey))
		.map((m) => m.display_name);
}
