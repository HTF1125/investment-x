import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Request Access | Investment-X',
  description: 'Apply for access to Investment-X quantitative research network and macro intelligence tools.',
};

export default function RegisterLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
