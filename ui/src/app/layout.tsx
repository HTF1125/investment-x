import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider } from '@/context/ThemeContext';
import { TaskProvider } from '@/components/TaskProvider';
import QueryProvider from '@/providers/QueryProvider';
import ErrorBoundary from '@/components/ErrorBoundary';
import SessionExpiredModal from '@/components/SessionExpiredModal';

export const viewport: Viewport = {
  themeColor: "#020617",
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
    <html lang="en" className="scroll-smooth">
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
