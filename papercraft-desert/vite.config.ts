import { iwsdkDev } from '@iwsdk/vite-plugin-dev';
import { defineConfig } from 'vite';
import mkcert from 'vite-plugin-mkcert';

export default defineConfig({
  plugins: [
    // HTTPS is required for WebXR; mkcert provisions a local trusted cert.
    mkcert(),
    // Dev server + in-browser WebXR emulator (no headset needed to iterate).
    // injectOnBuild bundles the emulator into the production build too, so the
    // hosted (GitHub Pages) demo is explorable on desktop with mouse/keyboard,
    // while a real headset still gets true WebXR.
    iwsdkDev({
      emulator: { device: 'metaQuest3', injectOnBuild: true },
      verbose: true,
    }),
  ],
  server: { host: '0.0.0.0', port: 8081, open: true },
  build: {
    outDir: 'dist',
    sourcemap: process.env.NODE_ENV !== 'production',
    target: 'esnext',
    rollupOptions: { input: './index.html' },
  },
  esbuild: { target: 'esnext' },
  optimizeDeps: { esbuildOptions: { target: 'esnext' } },
  publicDir: 'public',
  base: './',
});
