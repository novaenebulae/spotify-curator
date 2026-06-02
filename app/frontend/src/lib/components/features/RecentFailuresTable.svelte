<script lang="ts">
	import type { RecentFailure } from '$lib/featuresApi';
	import StatusBadge from '$lib/components/common/StatusBadge.svelte';

	let {
		failures,
		page = 1,
		pageSize = 10,
		onPageChange,
		onInspect
	}: {
		failures: RecentFailure[];
		page?: number;
		pageSize?: number;
		onPageChange?: (page: number) => void;
		onInspect?: (failure: RecentFailure) => void;
	} = $props();

	const totalPages = $derived(Math.max(1, Math.ceil(failures.length / pageSize)));
	const pageItems = $derived(
		failures.slice((page - 1) * pageSize, page * pageSize)
	);

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
				<th>Track</th>
				<th>Artists</th>
				<th>Status</th>
				<th>Error</th>
			</tr>
		</thead>
		<tbody>
			{#each pageItems as f (f.track_id)}
				<tr>
					<td class="track-col">
						{#if onInspect}
							<button type="button" class="title-inspect" onclick={() => onInspect(f)}>
								{f.title || `Track #${f.track_id}`}
							</button>
						{:else}
							{f.title || `Track #${f.track_id}`}
						{/if}
					</td>
					<td class="artists-col">{f.artist_names.join(', ') || '—'}</td>
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

{#if failures.length > pageSize}
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
	.track-col {
		min-width: 12rem;
		max-width: 20rem;
	}
	.artists-col {
		min-width: 8rem;
		max-width: 14rem;
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
