<script lang="ts">
	let {
		src = null,
		alt,
		size = 'md',
		href = null
	}: {
		src?: string | null;
		alt: string;
		size?: 'sm' | 'md' | 'lg';
		href?: string | null;
	} = $props();

	let failed = $state(false);

	const px = $derived(size === 'sm' ? 40 : size === 'lg' ? 64 : size === 'xl' ? 128 : 48);

	function onError(): void {
		failed = true;
	}
</script>

{#if href}
	<a
		class="album-cover-link"
		{href}
		target="_blank"
		rel="noopener noreferrer"
		title="Open in Spotify"
	>
		{#if src && !failed}
			<img
				class="album-cover"
				{src}
				{alt}
				width={px}
				height={px}
				loading="lazy"
				decoding="async"
				onerror={onError}
			/>
		{:else}
			<div class="album-cover fallback" style="width: {px}px; height: {px}px" aria-hidden="true">
				<span>♪</span>
			</div>
		{/if}
	</a>
{:else if src && !failed}
	<img
		class="album-cover"
		{src}
		{alt}
		width={px}
		height={px}
		loading="lazy"
		decoding="async"
		onerror={onError}
	/>
{:else}
	<div class="album-cover fallback" style="width: {px}px; height: {px}px" aria-hidden="true">
		<span>♪</span>
	</div>
{/if}

<style>
	.album-cover-link {
		display: inline-block;
		flex-shrink: 0;
		line-height: 0;
	}
	.album-cover-link:hover {
		text-decoration: none;
	}
	.album-cover {
		display: block;
		border-radius: 4px;
		object-fit: contain;
		background: var(--color-surface-elevated);
	}
	.fallback {
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 4px;
		background: var(--color-surface-elevated);
		border: 1px solid var(--color-border);
		color: var(--color-muted);
		font-size: 1.25rem;
	}
</style>
