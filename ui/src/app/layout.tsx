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
          className="absolute -top-10 left-0 z-[9999] bg-background text-foreground p-2 border border-border focus:top-0 transition-[top]"
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
