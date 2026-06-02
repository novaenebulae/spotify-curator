<script lang="ts">
	import CollapsibleSection from '$lib/components/common/CollapsibleSection.svelte';
	import type { CoverageField, FeatureCoverage } from '$lib/featuresApi';

	type Props = {
		fields: CoverageField[];
		fieldsBySource?: FeatureCoverage['fields_by_source'];
		loading?: boolean;
	};

	let { fields, fieldsBySource = null, loading = false }: Props = $props();

	const KEY_FIELDS = ['bpm', 'energy', 'danceability', 'valence', 'loudness', 'key'];

	const rbFields = $derived(fieldsBySource?.reccobeats?.length ? fieldsBySource.reccobeats : fields);
	const essFields = $derived(fieldsBySource?.essentia_lowlevel ?? []);

	function pickKey(list: CoverageField[]): CoverageField[] {
		const byName = new Map(list.map((f) => [f.field, f]));
		return KEY_FIELDS.map((k) => byName.get(k)).filter((f): f is CoverageField => f != null);
	}

	const rbKey = $derived(pickKey(rbFields));
	const essKey = $derived(pickKey(essFields));
</script>

<CollapsibleSection title="Field coverage" collapsed={true} storageKey="features_field_coverage_open">
	{#if loading}
		<p class="muted">Loading…</p>
	{:else if rbKey.length === 0 && essKey.length === 0}
		<p class="muted">No field statistics yet. Run enrichment first.</p>
	{:else}
		<div class="coverage-grid">
			<table class="compact-table">
				<thead>
					<tr>
						<th>Field</th>
						<th>ReccoBeats</th>
						<th>Essentia</th>
					</tr>
				</thead>
				<tbody>
					{#each KEY_FIELDS as key}
						{@const rb = rbKey.find((f) => f.field === key)}
						{@const es = essKey.find((f) => f.field === key)}
						{#if rb || es}
							<tr>
								<td class="field-name">{key}</td>
								<td class="num"
									>{rb ? `${rb.coverage_percent.toFixed(1)}%` : '—'}</td
								>
								<td class="num">{es ? `${es.coverage_percent.toFixed(1)}%` : '—'}</td>
							</tr>
						{/if}
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</CollapsibleSection>

<style>
	.coverage-grid {
		overflow-x: auto;
	}
	.compact-table {
		width: auto;
		max-width: 100%;
		border-collapse: collapse;
		font-size: 0.88rem;
	}
	.compact-table th,
	.compact-table td {
		padding: 0.35rem 0.75rem;
		border-bottom: 1px solid var(--color-border);
		text-align: left;
	}
	.compact-table th:not(:first-child),
	.compact-table td.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.field-name {
		color: var(--color-muted);
	}
</style>
