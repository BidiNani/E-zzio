import { sveltekit } from '@sveltejs/kit/vite';

const backend = 'http://127.0.0.1:8000';

export default {
  plugins: [sveltekit()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    open: false,
    proxy: {
      '/api': backend,
      '/status': backend,
      '/router-status': backend,
      '/maintenance': backend,
      '/safe-actions': backend,
      '/cloud-brain': backend,
      '/commander': backend,
      '/human': backend,
      '/human-chat': backend,
      '/supervisor': backend,
      '/performance': backend,
      '/forge': backend,
      '/vision': backend
    }
  }
};
