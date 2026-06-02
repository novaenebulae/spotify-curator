<script lang="ts">
	import {
		FIELD_LABELS,
		formatBpm,
		formatKeyMode,
		formatPercent,
		formatCamelot,
		MOOD_FIELDS,
		RHYTHM_FIELDS,
		TEXTURE_FIELDS
	} from '$lib/featureFormat';

	let {
		fields,
		showKey = true
	}: {
		fields: Record<string, number>;
		showKey?: boolean;
	} = $props();

	function displayValue(name: string, value: number): string {
		if (name === 'bpm') return formatBpm(value) ?? String(value);
		if (name === 'key') {
			const km = formatKeyMode(value, fields.mode);
			const cam = fields.mode !== undefined ? formatCamelot(value, fields.mode) : null;
			if (km && cam) return `${km} (${cam})`;
			return km ?? String(value);
		}
		if (name === 'mode') return value === 1 ? 'Major' : 'Minor';
		if (['energy', 'danceability', 'valence', 'acousticness', 'instrumentalness', 'speechiness', 'liveness'].includes(name)) {
			return formatPercent(value) ?? String(value);
		}
		return String(value);
	}

	const sections = $derived([
		{ title: 'Rhythm', keys: RHYTHM_FIELDS.filter((k) => fields[k] !== undefined) },
		{
			title: 'Tonality',
			keys: showKey
				? (['key'] as const).filter((k) => fields[k] !== undefined)
				: []
		},
		{ title: 'Mood', keys: MOOD_FIELDS.filter((k) => fields[k] !== undefined) },
		{ title: 'Texture', keys: TEXTURE_FIELDS.filter((k) => fields[k] !== undefined) },
		{
			title: 'Dynamics',
			keys: (['loudness'] as const).filter((k) => fields[k] !== undefined)
		}
	].filter((s) => s.keys.length > 0));
</script>

{#each sections as section (section.title)}
	<div class="metric-section">
		<h4>{section.title}</h4>
		<dl class="metric-grid">
			{#each section.keys as key (key)}
				<div class="metric-row">
					<dt>{FIELD_LABELS[key] ?? key}</dt>
					<dd>{displayValue(key, fields[key])}</dd>
				</div>
			{/each}
		</dl>
	</div>
{/each}

<style>
	.metric-section {
		margin-bottom: var(--space-lg);
	}
	.metric-section h4 {
		margin: 0 0 var(--space-sm);
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--color-muted);
	}
	.metric-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-sm) var(--space-md);
		margin: 0;
	}
	.metric-row dt {
		margin: 0;
		font-size: 0.8rem;
		color: var(--color-muted);
	}
	.metric-row dd {
		margin: 0;
		font-weight: 600;
	}
</style>
