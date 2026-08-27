import type { Metadata } from "next";
import { Montserrat, Open_Sans } from "next/font/google";
import "./globals.css";

const montserrat = Montserrat({
  subsets: ["latin"],
  weight: ["700", "800"],
  variable: "--font-montserrat",
  display: "swap",
});

const openSans = Open_Sans({
  subsets: ["latin"],
  weight: ["400", "600"],
  variable: "--font-open-sans",
  display: "swap",
});

// Canonical production URL — used to resolve relative OpenGraph/Twitter
// image and link URLs. Override via NEXT_PUBLIC_SITE_URL for preview/staging
// deploys; defaults to the real production domain otherwise.
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://azeonsystems.com.ng";

const TITLE = "Azeon Systems — Your Business, Seamlessly Connected.";
const DESCRIPTION =
  "The Enterprise Resource Suite for SMEs: HR, Finance, CRM, and Inventory, unified into one platform with real-time CEO dashboards.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: TITLE,
  description: DESCRIPTION,
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    url: "/",
    siteName: "Azeon Systems",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${montserrat.variable} ${openSans.variable}`}>
      <body className="font-body bg-white text-gray-900 antialiased">{children}</body>
    </html>
  );
}
