'use client';

import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import * as Cesium from 'cesium';

export interface GlobeControls {
  flyTo: (destination: { lat: number; lng: number; altitude?: number }, duration?: number) => Promise<void>;
  flyToEntity: (entityId: string) => Promise<void>;
  trackEntity: (entityId: string) => Promise<void>;
  untrackEntity: () => Promise<void>;
  toggleLayer: (layerId: string, enabled?: boolean) => Promise<void>;
  getLayerState: (layerId: string) => boolean;
  setVisualStyle: (styleId: number) => Promise<void>;
  resetGlobe: () => Promise<void>;
  getViewer: () => any;
  getScene: () => any;
  onEntityClick: (callback: (entity: any) => void) => () => void;
}

export interface GlobeContextValue {
  controls: GlobeControls | null;
  ready: boolean;
  registerComponents: (components: any) => void;
}

/**
 * Single source of truth for the Cesium viewer handoff.
 *
 * The component that builds the viewer (`GlobeViewerClient`) calls
 * `registerComponents`; every other consumer (`useCyberverseLayers`, the layer
 * panel, the page header) reads `ready`/`controls` from the same store.
 *
 * This used to be a plain hook, so each `useGlobe()` call owned its own refs
 * and `ready` flag. `registerComponents` then only updated the caller's copy —
 * the header stayed on "○ LOADING" and layer toggles were inert because the
 * consumers were watching a store that was never registered. It now lives in
 * one place and is shared through `<CyberverseGlobeProvider>`; use `useGlobe()`
 * below to consume it.
 */
export function useGlobeStore(): GlobeContextValue {
  const viewerRef = useRef<any>(null);
  const sceneRef = useRef<any>(null);
  const controlsRef = useRef<any>(null);
  const [ready, setReady] = useState(false);

  const registerComponents = useCallback((components: any) => {
    // The viewer can arrive either at the top level or bundled inside `scene`
    // (the gods-eye-view caller passes `{ scene: { viewer, ... } }`). Resolve
    // both shapes — `getViewer()` below is what the layer manager waits on, and
    // a missing viewer silently left the header stuck on "○ LOADING".
    viewerRef.current = components.viewer ?? components.scene?.viewer ?? null;
    sceneRef.current = components.scene;
    controlsRef.current = components.controls;
    setReady(true);
  }, []);

  const flyTo = useCallback(async (destination: { lat: number; lng: number; altitude?: number }, duration = 2) => {
    if (!viewerRef.current) return;
    const { lat, lng, altitude = 10000 } = destination;
    viewerRef.current.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(lng, lat, altitude),
      duration,
    });
  }, []);

  const flyToEntity = useCallback(async (entityId: string) => {
    if (!viewerRef.current) return;
    const entity = viewerRef.current.entities.getById(entityId);
    if (entity) {
      viewerRef.current.camera.flyTo(entity);
    }
  }, []);

  const trackEntity = useCallback(async (entityId: string) => {
    if (!viewerRef.current) return;
    const entity = viewerRef.current.entities.getById(entityId);
    if (entity) {
      viewerRef.current.trackedEntity = entity;
    }
  }, []);

  const untrackEntity = useCallback(async () => {
    if (!viewerRef.current) return;
    viewerRef.current.trackedEntity = undefined;
  }, []);

  const toggleLayer = useCallback(async (layerId: string, enabled?: boolean) => {
    if (!controlsRef.current) return;
    controlsRef.current.toggleLayer?.(layerId, enabled);
  }, []);

  const getLayerState = useCallback((layerId: string): boolean => {
    if (!controlsRef.current) return false;
    return controlsRef.current.getLayerState?.(layerId) ?? false;
  }, []);

  const setVisualStyle = useCallback(async (styleId: number) => {
    if (!controlsRef.current) return;
    controlsRef.current.setVisualStyle?.(styleId);
  }, []);

  const resetGlobe = useCallback(async () => {
    if (!viewerRef.current) return;
    viewerRef.current.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(0, 0, 20000000),
      duration: 2,
    });
    if (controlsRef.current) {
      controlsRef.current.resetGlobe?.();
    }
  }, []);

  const getViewer = useCallback(() => viewerRef.current, []);
  const getScene = useCallback(() => sceneRef.current, []);

  const onEntityClick = useCallback((callback: (entity: any) => void) => {
    if (!viewerRef.current) return () => {};
    const handler = viewerRef.current.screenSpaceEventHandler;
    const removeCallback = () => {
      handler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK);
    };
    handler.setInputAction((movement: any) => {
      const picked = viewerRef.current.scene.pick(movement.position);
      if (picked && picked.id) {
        callback(picked.id);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    return removeCallback;
  }, []);

  // Memoised so the context value identity is stable across renders that don't
  // actually change the viewer state — otherwise every consumer would re-render
  // (and the globe would re-initialise) on unrelated parent updates.
  const controls = useMemo<GlobeControls | null>(
    () =>
      ready
        ? {
            flyTo,
            flyToEntity,
            trackEntity,
            untrackEntity,
            toggleLayer,
            getLayerState,
            setVisualStyle,
            resetGlobe,
            getViewer,
            getScene,
            onEntityClick,
          }
        : null,
    [
      ready,
      flyTo,
      flyToEntity,
      trackEntity,
      untrackEntity,
      toggleLayer,
      getLayerState,
      setVisualStyle,
      resetGlobe,
      getViewer,
      getScene,
      onEntityClick,
    ],
  );

  return useMemo(() => ({ controls, ready, registerComponents }), [controls, ready, registerComponents]);
}

export const GlobeContext = createContext<GlobeContextValue | null>(null);

/** Consume the shared globe store. Must be inside `<CyberverseGlobeProvider>`. */
export function useGlobe(): GlobeContextValue {
  const value = useContext(GlobeContext);
  if (!value) {
    throw new Error('useGlobe() must be used within <CyberverseGlobeProvider>.');
  }
  return value;
}
