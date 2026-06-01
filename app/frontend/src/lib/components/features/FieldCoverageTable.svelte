<script lang="ts">
	import type { CoverageField } from '$lib/featuresApi';

	type Props = {
		fields: CoverageField[];
		loading?: boolean;
	};

	let { fields, loading = false }: Props = $props();
</script>

<section class="card">
	<h2>Field coverage</h2>
	{#if loading}
		<p class="muted">Loading…</p>
	{:else if fields.length === 0}
		<p class="muted">No field statistics yet. Run enrichment first.</p>
	{:else}
		<table class="data-table">
			<thead>
				<tr>
					<th>Field</th>
					<th>Available</th>
					<th>Coverage</th>
				</tr>
			</thead>
			<tbody>
				{#each fields as field}
					<tr>
						<td>{field.field}</td>
						<td>{field.available_count.toLocaleString()}</td>
						<td>{field.coverage_percent.toFixed(1)}%</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</section>
