import { iwsdkDev } from '@iwsdk/vite-plugin-dev';
import { defineConfig } from 'vite';
import mkcert from 'vite-plugin-mkcert';

export default defineConfig({
  plugins: [
    // HTTPS is required for WebXR; mkcert provisions a local trusted cert.
    mkcert(),
    // Dev server + in-browser WebXR emulator (no headset needed to iterate).
    // Note: the emulator is intentionally NOT injected into the production
    // build, so the hosted site gives real headsets true WebXR and everyone
    // else the live-rendered (animated) scene. To let desktop visitors free-look
    // the hosted demo, add `injectOnBuild: true, activation: 'always'` below —
    // but that shadows native VR on real headsets, so it's left off by default.
    iwsdkDev({
      emulator: { device: 'metaQuest3' },
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
