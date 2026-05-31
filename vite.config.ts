import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  build: {
    lib: {
      entry: path.resolve(__dirname, 'src/main.ts'),
      formats: ['iife'],
      name: 'App',
      fileName: () => 'bundle.js',
    },
    outDir: 'product_cleaner/static/dist',
    emptyOutDir: true,
  },
});
