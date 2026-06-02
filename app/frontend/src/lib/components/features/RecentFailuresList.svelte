<script lang="ts">
	import CollapsibleSection from '$lib/components/common/CollapsibleSection.svelte';
	import RecentFailuresTable from '$lib/components/features/RecentFailuresTable.svelte';
	import { FAILURES_CLEARED_STORAGE_KEY, type FailurePage, type RecentFailure } from '$lib/featuresApi';

	type Props = {
		failures: FailurePage | null;
		busy?: boolean;
		onPageChange?: (page: number) => void;
		onInspect?: (failure: RecentFailure) => void;
		onCleared?: () => void;
	};

	let { failures, busy = false, onPageChange, onInspect, onCleared }: Props = $props();

	function clearFailures() {
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem(FAILURES_CLEARED_STORAGE_KEY, new Date().toISOString());
		}
		onCleared?.();
	}
</script>

<CollapsibleSection title="Recent failures" collapsed={true} storageKey="features_recent_failures_open">
	<div class="toolbar">
		{#if failures && failures.total > 0}
			<button type="button" class="secondary small" onclick={clearFailures}>Clear list</button>
			<span class="muted">{failures.total} failure(s)</span>
		{/if}
	</div>
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
</CollapsibleSection>

<style>
	.toolbar {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		margin-bottom: var(--space-md);
	}
	button.small {
		font-size: 0.85rem;
		padding: 0.25rem 0.6rem;
	}
</style>
