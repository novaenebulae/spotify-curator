<script lang="ts">
	let {
		variant = 'neutral',
		label
	}: {
		variant?: 'liked' | 'unavailable' | 'duplicate' | 'missing' | 'neutral';
		label: string;
	} = $props();
</script>

<span class="badge badge-{variant}">{label}</span>
