<script lang="ts">
	import RecentFailuresTable from '$lib/components/features/RecentFailuresTable.svelte';
	import type { RecentFailure } from '$lib/featuresApi';

	type Props = {
		failures: RecentFailure[];
		busy?: boolean;
		onRetry?: () => void;
		onInspect?: (failure: RecentFailure) => void;
	};

	let { failures, busy = false, onRetry, onInspect }: Props = $props();

	let page = $state(1);
	const pageSize = 10;

	$effect(() => {
		failures;
		page = 1;
	});
</script>

<section class="card">
	<h2>Recent failures</h2>
	{#if failures.length === 0}
		<p class="muted">No recent failures.</p>
	{:else}
		<RecentFailuresTable
			{failures}
			{page}
			{pageSize}
			onPageChange={(p) => (page = p)}
			{onInspect}
		/>
		<div class="row">
			<button type="button" class="secondary" disabled={busy} onclick={() => onRetry?.()}>
				Retry failed
			</button>
		</div>
	{/if}
</section>
