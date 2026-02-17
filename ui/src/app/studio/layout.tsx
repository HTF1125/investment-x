import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Analysis Studio | Investment-X',
  description: 'Create and customize charts with the Investment-X Analysis Studio. Build custom visualizations with live data.',
};

export default function StudioLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
