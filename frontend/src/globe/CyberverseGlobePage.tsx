'use client';

import { useState, useEffect } from 'react';
import { CyberverseGlobe } from './GlobeViewer';
import { GlobeLayerPanel } from './GlobeLayerPanel';
import { useCyberverseLayers } from './useCyberverseLayers';
import { CesiumPreloader } from '@/app/ClientComponents';

export function CyberverseGlobePage() {
  const [labId, setLabId] = useState<string>('');
  const { loadLabEnvironment, loadNetworkTopology, layerState, toggleLayer, ready } = useCyberverseLayers();

  const handleLoadLab = async (e: React.FormEvent) => {
    e.preventDefault();
    if (labId) {
      await loadLabEnvironment(labId);
      // Also enable network topology layer
      if (!layerState.networkTopology) {
        toggleLayer('networkTopology', true);
      }
    }
  };

  const handleLoadTopology = async (e: React.FormEvent) => {
    e.preventDefault();
    if (labId) {
      await loadNetworkTopology(labId);
      if (!layerState.networkTopology) {
        toggleLayer('networkTopology', true);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <CesiumPreloader />
      <header className="fixed top-0 left-0 right-0 z-30 bg-gray-900/95 backdrop-blur-sm border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
              Cyberverse Globe
            </h1>
            <span className="px-2 py-0.5 text-xs font-mono bg-gray-800 border border-gray-700 rounded">
              {ready ? '● LIVE' : '○ LOADING'}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <form onSubmit={handleLoadLab} className="flex items-center gap-2">
              <input
                type="text"
                value={labId}
                onChange={(e) => setLabId(e.target.value)}
                placeholder="Lab ID (UUID)"
                className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm font-mono text-white placeholder-gray-500 focus:border-cyan-500 focus:outline-none w-48"
              />
              <button type="submit" className="px-3 py-1.5 bg-cyan-500 hover:bg-cyan-600 text-gray-950 text-sm font-medium rounded transition-colors">
                Load Lab
              </button>
            </form>
            <form onSubmit={handleLoadTopology} className="flex items-center gap-2">
              <button type="submit" className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded transition-colors">
                Load Topology
              </button>
            </form>
          </div>
        </div>
      </header>

      <main className="pt-16 h-screen relative">
        <div className="absolute inset-0">
          <CyberverseGlobe
            initialLayers={['flights', 'satellites', 'earthquakes']}
            style={{ width: '100%', height: '100%' }}
          />
        </div>
        <GlobeLayerPanel />
      </main>
    </div>
  );
}

export default CyberverseGlobePage;