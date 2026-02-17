import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Timeseries Manager | Investment-X Admin',
  description: 'Administrative interface for managing timeseries data sources and configurations.',
};

export default function AdminTimeseriesLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
