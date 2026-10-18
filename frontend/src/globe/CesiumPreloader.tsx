'use client';

import { useEffect } from 'react';

/**
 * Warms the Cesium engine + its WASM assets shortly after the globe mounts.
 *
 * This lives in src/globe/ rather than the shared app/ClientComponents module
 * so it can only ever be pulled into the /globe route chunk — it must never
 * reach pages that do not render a 3D globe.
 */
export default function CesiumPreloader() {
  useEffect(() => {
    const timer = setTimeout(() => {
      import('./cesium-loader')
        .then(({ preloadCesium, preloadCesiumAssets }) => {
          preloadCesiumAssets();
          preloadCesium();
        })
        .catch(() => {
          /* preloading is best-effort */
        });
    }, 3000);
    return () => clearTimeout(timer);
  }, []);
  return null;
}