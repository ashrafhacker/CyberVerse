'use client';

import { type ReactNode } from 'react';
import { GlobeContext, useGlobeStore } from './useGlobe';
import { CyberverseLayersContext, useCyberverseLayersStore } from './useCyberverseLayers';

/**
 * Provides one shared globe store and one shared Cyberverse layer store to the
 * `/globe` subtree, so the Cesium viewer, the header status badge, the layer
 * panel and the lab-loading forms all read and mutate the same state.
 *
 * Wrap the globe page in this before using `useGlobe()` /
 * `useCyberverseLayers()`.
 */
export function CyberverseGlobeProvider({ children }: { children: ReactNode }) {
  const globe = useGlobeStore();
  const layers = useCyberverseLayersStore(globe);

  return (
    <GlobeContext.Provider value={globe}>
      <CyberverseLayersContext.Provider value={layers}>
        {children}
      </CyberverseLayersContext.Provider>
    </GlobeContext.Provider>
  );
}

export default CyberverseGlobeProvider;
