import RouteSkeleton from '@/components/RouteSkeleton';

// Suspense boundary: shows the themed skeleton while the client page loads.
export default function Loading() {
  return <RouteSkeleton title="contact" />;
}
