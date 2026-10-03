'use client';

import { useState } from 'react';
import { useCyberverseLayers, LayerState } from './useCyberverseLayers';

const LAYER_CONFIG: Record<keyof LayerState, { label: string; icon: string; description: string }> = {
  threatIntel: { label: 'Threat Intel', icon: '🎯', description: 'CVEs, threat indicators, attack techniques' },
  socAlerts: { label: 'SOC Alerts', icon: '🚨', description: 'Live SOC alerts and incidents' },
  networkTopology: { label: 'Network Topology', icon: '🌐', description: 'Network infrastructure and connections' },
  liveAttacks: { label: 'Live Attacks', icon: '⚡', description: 'Real-time attack paths and vectors' },
  honeypots: { label: 'Honeypots', icon: '🍯', description: 'Global honeypot sensor network' },
  malwareDistribution: { label: 'Malware Distribution', icon: '🦠', description: 'Malware family geographic distribution' },
  vulnerabilityHeatmap: { label: 'Vuln Heatmap', icon: '🔓', description: 'CVE exploitation geographic heatmap' },
};

export function GlobeLayerPanel() {
  const { layerState, loading, toggleLayer, clearAll, ready } = useCyberverseLayers();
  const [expanded, setExpanded] = useState(true);

  if (!ready) {
    return (
      <div className="fixed bottom-4 right-4 z-40">
        <div className="bg-gray-900/90 backdrop-blur-sm rounded-lg border border-gray-700 p-3 text-cyan-400 font-mono text-sm">
          Initializing Globe...
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-40 w-72">
      <div className="bg-gray-900/90 backdrop-blur-sm rounded-lg border border-gray-700 overflow-hidden">
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-between p-3 hover:bg-gray-800 transition-colors"
        >
          <span className="flex items-center gap-2 text-cyan-400 font-mono text-sm">
            <span className="text-lg">🌐</span>
            <span>Cyberverse Layers</span>
          </span>
          <span className={`transition-transform ${expanded ? 'rotate-180' : ''}`}>▼</span>
        </button>

        {expanded && (
          <div className="p-3 space-y-2 border-t border-gray-700">
            {Object.entries(LAYER_CONFIG).map(([key, config]) => {
              const layerKey = key as keyof LayerState;
              const enabled = layerState[layerKey];
              const isLoading = loading[layerKey];
              
              return (
                <label key={key} className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(e) => toggleLayer(layerKey, e.target.checked)}
                    disabled={isLoading}
                    className="w-4 h-4 accent-cyan-500 rounded"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-white text-sm">
                      <span>{config.icon}</span>
                      <span className="font-medium truncate">{config.label}</span>
                      {isLoading && <span className="text-xs text-yellow-400 animate-pulse">Loading...</span>}
                    </div>
                    <div className="text-xs text-gray-400 truncate">{config.description}</div>
                  </div>
                </label>
              );
            })}
            <button
              onClick={clearAll}
              className="w-full mt-2 px-3 py-1.5 text-xs text-gray-400 hover:text-red-400 border border-gray-700 rounded hover:border-red-500 transition-colors"
            >
              Clear All Layers
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default GlobeLayerPanel;