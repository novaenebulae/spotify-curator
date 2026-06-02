<script lang="ts">
	let {
		variant = 'neutral',
		label
	}: {
		variant?:
			| 'liked'
			| 'unavailable'
			| 'duplicate'
			| 'missing'
			| 'neutral'
			| 'running'
			| 'idle'
			| 'warning';
		label: string;
	} = $props();
</script>

<span class="badge badge-{variant}">{label}</span>
