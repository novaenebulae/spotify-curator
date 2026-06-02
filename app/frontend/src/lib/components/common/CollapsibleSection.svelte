<script lang="ts">
	let {
		title,
		collapsed = true,
		storageKey = '',
		children
	}: {
		title: string;
		collapsed?: boolean;
		storageKey?: string;
		children?: import('svelte').Snippet;
	} = $props();

	let open = $state(!collapsed);

	$effect(() => {
		if (!storageKey || typeof localStorage === 'undefined') return;
		const stored = localStorage.getItem(storageKey);
		if (stored === 'open') open = true;
		else if (stored === 'closed') open = false;
	});

	function toggle() {
		open = !open;
		if (storageKey && typeof localStorage !== 'undefined') {
			localStorage.setItem(storageKey, open ? 'open' : 'closed');
		}
	}
</script>

<section class="card collapsible">
	<button type="button" class="collapsible-header" aria-expanded={open} onclick={toggle}>
		<span class="chevron" class:open>{open ? '▼' : '▶'}</span>
		<h2>{title}</h2>
	</button>
	{#if open}
		<div class="collapsible-body">
			{@render children?.()}
		</div>
	{/if}
</section>

<style>
	.collapsible {
		padding: 0;
		overflow: hidden;
	}
	.collapsible-header {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		width: 100%;
		padding: var(--space-md) var(--space-lg);
		background: none;
		border: none;
		color: inherit;
		cursor: pointer;
		text-align: left;
	}
	.collapsible-header h2 {
		margin: 0;
		font-size: 1.1rem;
	}
	.chevron {
		font-size: 0.75rem;
		color: var(--color-muted);
		width: 1rem;
		flex-shrink: 0;
	}
	.collapsible-body {
		padding: 0 var(--space-lg) var(--space-lg);
	}
	.collapsible-body :global(> section.card) {
		box-shadow: none;
		padding: 0;
		margin: 0;
	}
</style>
