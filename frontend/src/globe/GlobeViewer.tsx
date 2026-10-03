'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';

const GlobeViewer = dynamic(
  () => import('./GlobeViewerClient').then((mod) => mod.GlobeViewerClient),
  { 
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex items-center justify-center bg-gray-950">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-cyan-400 font-mono text-sm">Initializing Cyberverse Globe...</p>
        </div>
      </div>
    )
  }
);

interface GlobeViewerProps {
  className?: string;
  style?: React.CSSProperties;
  initialLayers?: string[];
  onReady?: (viewer: any) => void;
  onError?: (error: Error) => void;
}

export function CyberverseGlobe({
  className = '',
  style,
  initialLayers = [],
  onReady,
  onError,
}: GlobeViewerProps) {
  return (
    <div className={`w-full h-full ${className}`} style={{ ...style, position: 'relative' }}>
      <GlobeViewer
        initialLayers={initialLayers}
        onReady={onReady}
        onError={onError}
      />
    </div>
  );
}

export default CyberverseGlobe;