import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Insights | Investment-X',
  description: 'Research PDF library for macro and quantitative analysis.',
};

export default function InsightsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
