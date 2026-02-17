import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Intel Feed | Investment-X',
  description: 'Real-time intelligence feed aggregating Telegram channels for macro and quantitative research signals.',
};

export default function IntelLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
