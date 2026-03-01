import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider } from '@/context/ThemeContext';
import { TaskProvider } from '@/components/TaskProvider';
import QueryProvider from '@/providers/QueryProvider';
import ErrorBoundary from '@/components/ErrorBoundary';

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
        <QueryProvider>
          <AuthProvider>
            <TaskProvider>
              <ThemeProvider>
                <ErrorBoundary>
                  {children}
                </ErrorBoundary>
              </ThemeProvider>
            </TaskProvider>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
