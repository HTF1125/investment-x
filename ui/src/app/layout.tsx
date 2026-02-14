import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from '@/context/AuthContext';
import QueryProvider from '@/providers/QueryProvider';

export const metadata: Metadata = {
  title: "Investment-X | Macro Intelligence",
  description: "Advanced Macro Research & Quantitative Intelligence Library",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="scroll-smooth">
      <body>
        <QueryProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
