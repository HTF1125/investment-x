import type { Metadata, Viewport } from "next";
import { Inter, Space_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider } from '@/context/ThemeContext';
import { TaskProvider } from '@/components/TaskProvider';
import QueryProvider from '@/providers/QueryProvider';
import ErrorBoundary from '@/components/ErrorBoundary';
import SessionExpiredModal from '@/components/SessionExpiredModal';

const body = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-body",
  display: "swap",
});

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
    <html lang="en" className={`scroll-smooth ${body.variable} ${mono.variable}`}>
      <body>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 focus:z-[9999] focus:bg-background focus:text-foreground focus:p-2 focus:border focus:border-border"
        >
          Skip to main content
        </a>
        <QueryProvider>
          <AuthProvider>
            <TaskProvider>
              <ThemeProvider>
                <ErrorBoundary>
                  {children}
                  <SessionExpiredModal />
                </ErrorBoundary>
              </ThemeProvider>
            </TaskProvider>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
