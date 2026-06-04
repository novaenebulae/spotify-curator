<script lang="ts">
	import type { RecentFailure } from '$lib/featuresApi';
	import StatusBadge from '$lib/components/common/StatusBadge.svelte';

	function formatWhen(iso: string | null | undefined): string {
		if (!iso) return '—';
		try {
			const d = new Date(iso);
			return d.toLocaleString(undefined, {
				month: 'short',
				day: 'numeric',
				hour: '2-digit',
				minute: '2-digit'
			});
		} catch {
			return iso.slice(0, 16);
		}
	}

	let {
		failures,
		page = 1,
		pageSize = 10,
		total = failures.length,
		onPageChange,
		onInspect
	}: {
		failures: RecentFailure[];
		page?: number;
		pageSize?: number;
		total?: number;
		onPageChange?: (page: number) => void;
		onInspect?: (failure: RecentFailure) => void;
	} = $props();

	const totalPages = $derived(Math.max(1, Math.ceil(total / pageSize)));

	function failureStatusVariant(status: string): 'missing' | 'unavailable' | 'neutral' {
		if (status === 'failed') return 'unavailable';
		if (status === 'not_found') return 'missing';
		return 'neutral';
	}
</script>

<div class="table-sticky-wrap failures-table">
	<table>
		<thead>
			<tr>
				<th>When</th>
				<th>Source</th>
				<th>Stage</th>
				<th>Feature</th>
				<th>Model</th>
				<th>Track</th>
				<th>Status</th>
				<th>Error</th>
			</tr>
		</thead>
		<tbody>
			{#each failures as f (f.id)}
				<tr>
					<td class="when-col">{formatWhen(f.occurred_at)}</td>
					<td class="source-col">{f.source ?? '—'}</td>
					<td class="narrow">{f.stage_name ?? '—'}</td>
					<td class="narrow">{f.feature_name ?? '—'}</td>
					<td class="narrow">{f.model_name ?? '—'}</td>
					<td class="track-col">
						{#if onInspect}
							<button type="button" class="title-inspect" onclick={() => onInspect(f)}>
								{f.title || `Track #${f.track_id}`}
							</button>
						{:else}
							{f.title || `Track #${f.track_id}`}
						{/if}
					</td>
					<td>
						<StatusBadge variant={failureStatusVariant(f.status)} label={f.status} />
					</td>
					<td class="error-cell" title={f.error_message ?? f.error_code ?? ''}>
						{f.error_message ?? f.error_code ?? '—'}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

{#if totalPages > 1}
	<div class="row pagination">
		<button
			type="button"
			class="secondary"
			disabled={page <= 1}
			onclick={() => onPageChange?.(page - 1)}>←</button
		>
		<span class="muted">Page {page} / {totalPages}</span>
		<button
			type="button"
			class="secondary"
			disabled={page >= totalPages}
			onclick={() => onPageChange?.(page + 1)}>→</button
		>
	</div>
{/if}

<style>
	.failures-table {
		max-height: min(50vh, 420px);
	}
	.when-col {
		min-width: 7rem;
		max-width: 9rem;
		font-size: 0.8rem;
		color: var(--color-muted);
		white-space: nowrap;
	}
	.source-col {
		min-width: 7rem;
		max-width: 10rem;
		font-size: 0.85rem;
		color: var(--color-muted);
	}
	.track-col {
		min-width: 12rem;
		max-width: 20rem;
	}
	.title-inspect {
		background: none;
		border: none;
		color: var(--color-accent);
		padding: 0;
		font: inherit;
		font-weight: 600;
		cursor: pointer;
		text-align: left;
		text-decoration: underline;
		text-underline-offset: 2px;
	}
	.error-cell {
		font-size: 0.85rem;
		max-width: 24rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.pagination {
		margin-top: var(--space-md);
		align-items: center;
		gap: var(--space-md);
	}
</style>
