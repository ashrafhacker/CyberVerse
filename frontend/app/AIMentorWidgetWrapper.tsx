'use client';

import dynamic from 'next/dynamic';

const AIMentorWidget = dynamic(() => import('@/components/AIMentorWidget'), {
  ssr: false,
  loading: () => null,
});

export default function AIMentorWidgetWrapper() {
  return <AIMentorWidget />;
}