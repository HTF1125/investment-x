import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Sign In | Investment-X',
  description: 'Sign in to access Investment-X quantitative intelligence and macro research tools.',
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
