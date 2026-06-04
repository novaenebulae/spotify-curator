<script lang="ts">
	import CollapsibleSection from '$lib/components/common/CollapsibleSection.svelte';
	import StatusBadge from '$lib/components/common/StatusBadge.svelte';
	import type { AdvancedFailure } from '$lib/featuresApi';

	type Props = {
		failures: AdvancedFailure[];
		loading?: boolean;
		onInspect?: (failure: AdvancedFailure) => void;
	};

	let { failures, loading = false, onInspect }: Props = $props();
</script>

<CollapsibleSection
	title="Advanced analysis failures"
	collapsed={true}
	storageKey="features_advanced_failures_open"
>
	{#if loading}
		<p class="muted">Loading…</p>
	{:else if failures.length === 0}
		<p class="muted">No recent advanced failures.</p>
	{:else}
		<div class="table-sticky-wrap failures-table">
			<table>
				<thead>
					<tr>
						<th>Track</th>
						<th>Feature</th>
						<th>Model</th>
						<th>Status</th>
						<th>Error</th>
					</tr>
				</thead>
				<tbody>
					{#each failures as f (f.track_id + f.feature_name)}
						<tr>
							<td>
								{#if onInspect}
									<button type="button" class="link" onclick={() => onInspect(f)}>
										{f.title || `Track #${f.track_id}`}
									</button>
								{:else}
									{f.title || `Track #${f.track_id}`}
								{/if}
							</td>
							<td><code>{f.feature_name}</code></td>
							<td class="muted">{f.model_name ?? '—'}</td>
							<td>
								<StatusBadge
									variant={f.status === 'model_missing' ? 'warning' : 'unavailable'}
									label={f.status}
								/>
							</td>
							<td class="err-col" title={f.error_message ?? ''}>
								{f.error_code ?? f.error_message?.slice(0, 80) ?? '—'}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</CollapsibleSection>

<style>
	button.link {
		background: none;
		border: none;
		color: var(--color-accent);
		cursor: pointer;
		padding: 0;
		text-align: left;
		text-decoration: underline;
	}
	.err-col {
		max-width: 14rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: 0.85rem;
	}
	code {
		font-size: 0.8rem;
	}
</style>
