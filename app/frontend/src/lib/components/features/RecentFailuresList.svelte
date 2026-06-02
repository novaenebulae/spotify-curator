<script lang="ts">
	import RecentFailuresTable from '$lib/components/features/RecentFailuresTable.svelte';
	import type { FailurePage, RecentFailure } from '$lib/featuresApi';

	type Props = {
		failures: FailurePage | null;
		busy?: boolean;
		onPageChange?: (page: number) => void;
		onInspect?: (failure: RecentFailure) => void;
	};

	let { failures, busy = false, onPageChange, onInspect }: Props = $props();
</script>

<section class="card">
	<h2>Recent failures</h2>
	{#if !failures || failures.total === 0}
		<p class="muted">No recent failures.</p>
	{:else}
		<RecentFailuresTable
			failures={failures.items}
			page={failures.page}
			pageSize={failures.page_size}
			total={failures.total}
			onPageChange={(p) => onPageChange?.(p)}
			{onInspect}
		/>
		{#if busy}
			<p class="muted">Loading…</p>
		{/if}
	{/if}
</section>
