import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Admin Manager | Investment-X',
  description: 'Administrative interface for managing timeseries and users.',
};

export default function AdminTimeseriesLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
