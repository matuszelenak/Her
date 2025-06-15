<script lang="ts">
    import "../app.css";
    import { QueryClientProvider } from '@tanstack/svelte-query'
    import { SvelteQueryDevtools } from '@tanstack/svelte-query-devtools'
    import type { PageData } from './$types'
    import '../app.css'
    
    export let data: PageData
</script>

<QueryClientProvider client={data.queryClient}>
    <div class="grid grid-cols-[auto_1fr]">
        <aside class="sticky top-0 col-span-1 h-screen">
            <h2 class="text-xl font-semibold mb-4 text-gray-800">Navigation</h2>
            <nav>
                <a href="#" class="nav-link text-blue-600 hover:text-blue-800">Dashboard</a>
                <a href="#" class="nav-link text-blue-600 hover:text-blue-800">Profile</a>
                <a href="#" class="nav-link text-blue-600 hover:text-blue-800">Settings</a>
                <a href="#" class="nav-link text-blue-600 hover:text-blue-800">Messages</a>
                <a href="#" class="nav-link text-blue-600 hover:text-blue-800">Logout</a>
            </nav>
        </aside>
        <main class="col-span-1 p-4">
            <slot />
        </main>
    </div>


    <SvelteQueryDevtools />
</QueryClientProvider>

<style>
    .nav-link {
        display: block;
        padding: 0.5rem 1rem;
        border-bottom: 1px solid #ccc;
        transition: background-color 0.3s ease;
    }
    .nav-link:hover {
        background-color: #d0d0d0;
    }
    .nav-link:last-child {
        border-bottom: none;
    }
</style>
