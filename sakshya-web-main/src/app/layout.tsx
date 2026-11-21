import type { Metadata, Viewport } from 'next';
import { Noto_Sans } from 'next/font/google';
import './globals.css';

const notoSans = Noto_Sans({
  subsets: ['latin', 'devanagari'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-noto-sans',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'ASHA Voice Field Register | Saakshya Healthcare Platform',
  description:
    'Voice-first multilingual healthcare field register and PHC supervisor command center for ASHA workers.',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="hi-IN" className={notoSans.variable}>
      <body className="font-sans bg-clinical-canvas text-clinical-text antialiased min-h-screen">
        <a
          href="#main-content"
          className="sr-only-focusable fixed top-3 left-3 z-50 bg-clinical-primary text-white px-4 py-2 rounded-lg font-semibold text-sm shadow-lg"
        >
          Skip to main content
        </a>
        {children}
      </body>
    </html>
  );
}
