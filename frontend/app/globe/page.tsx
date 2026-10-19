'use client';

import { CyberverseGlobePage } from '@/src/globe/CyberverseGlobePage';
import { CyberverseGlobeProvider } from '@/src/globe/CyberverseGlobeProvider';

export default function GlobePage() {
  return (
    <CyberverseGlobeProvider>
      <CyberverseGlobePage />
    </CyberverseGlobeProvider>
  );
}
