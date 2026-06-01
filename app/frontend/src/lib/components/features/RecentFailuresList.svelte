<script lang="ts">
	import type { RecentFailure } from '$lib/featuresApi';

	type Props = {
		failures: RecentFailure[];
		busy?: boolean;
		onRetry?: () => void;
	};

	let { failures, busy = false, onRetry }: Props = $props();
</script>

<section class="card">
	<h2>Recent failures</h2>
	{#if failures.length === 0}
		<p class="muted">No recent failures.</p>
	{:else}
		<table class="data-table">
			<thead>
				<tr>
					<th>Track</th>
					<th>Artist</th>
					<th>Status</th>
					<th>Error</th>
				</tr>
			</thead>
			<tbody>
				{#each failures as f}
					<tr>
						<td>{f.title}</td>
						<td>{f.artist_names.join(', ') || '—'}</td>
						<td>{f.status}</td>
						<td class="error-cell">{f.error_message ?? f.error_code ?? '—'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
		<div class="row">
			<button type="button" class="secondary" disabled={busy} onclick={() => onRetry?.()}>
				Retry failed
			</button>
		</div>
	{/if}
</section>

<style>
	.error-cell {
		font-size: 0.85rem;
		max-width: 20rem;
		overflow: hidden;
		text-overflow: ellipsis;
	}
</style>
