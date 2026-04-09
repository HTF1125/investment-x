import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Admin | Investment-X',
  description: 'Administrative interface for managing timeseries, users, and system settings.',
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
