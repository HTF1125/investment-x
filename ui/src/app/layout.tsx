import type { Metadata, Viewport } from "next";
import { Space_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider } from '@/context/ThemeContext';

import QueryProvider from '@/providers/QueryProvider';
import ErrorBoundary from '@/components/shared/ErrorBoundary';
import SessionExpiredModal from '@/components/auth/SessionExpiredModal';

// Global mono-first typography. Space Mono is the only web font loaded — it
// drives --font-mono which the body and every chart/label inherit, so every
// surface in the app shares a single type voice.
const mono = Space_Mono({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-mono",
  display: "swap",
});


export const viewport: Viewport = {
  themeColor: "#080a10",
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  title: "Investment-X | Macro Intelligence",
  description: "Advanced Macro Research & Quantitative Intelligence Library",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/icon.svg", type: "image/svg+xml" },
    ],
    apple: "/icon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`scroll-smooth ${mono.variable}`}>
      <body>
        <a
          href="#main-content"
          className="absolute -top-10 left-0 z-[9999] bg-background text-foreground p-2 border border-border focus:top-0 transition-[top]"
        >
          Skip to main content
        </a>
        <QueryProvider>
          <AuthProvider>
            <ThemeProvider>
              <ErrorBoundary>
                {children}
                <SessionExpiredModal />
              </ErrorBoundary>
            </ThemeProvider>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
