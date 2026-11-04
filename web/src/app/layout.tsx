import type { Metadata, Viewport } from "next";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { AppShell } from "@/components/AppShell";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-jakarta", weight: ["600", "700", "800"] });

export const metadata: Metadata = {
  title: { default: "Food omniScan: Know what's inside", template: "%s · Food omniScan" },
  description: "Scan packaged food to see a transparent health score, ingredient explanations, allergen alerts and healthier alternatives. US FDA standards.",
  icons: { icon: "/logo.svg" },
  applicationName: "Food omniScan",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0d1310" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-US" className={`${inter.variable} ${jakarta.variable}`}>
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
