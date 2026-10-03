import { useCallback, useRef, useState } from 'react';
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

export function useGlobe(): { controls: GlobeControls | null; ready: boolean } {
  const viewerRef = useRef<any>(null);
  const sceneRef = useRef<any>(null);
  const controlsRef = useRef<any>(null);
  const [ready, setReady] = useState(false);

  const registerComponents = useCallback((components: any) => {
    viewerRef.current = components.viewer;
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

  const controls = ready
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
    : null;

  return { controls, ready, registerComponents };
}