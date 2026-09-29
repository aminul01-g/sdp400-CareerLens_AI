/**
 * Root layout.
 *
 * Server component. It mounts the three client providers and imports the global
 * stylesheet. The stylesheet content is carried over from the predecessor's
 * `src/index.css` unchanged — only the import site moved — so the design tokens
 * and therefore the whole visual identity are preserved.
 */
import type { Metadata, Viewport } from "next";
import { Toaster } from "@/components/ui/toaster";
import { AuthProvider } from "@/components/providers/AuthProvider";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { ThemeProvider } from "@/components/providers/ThemeProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "CareerLens AI — AI-Powered Job & Career Recommendations",
    template: "%s | CareerLens AI",
  },
  description:
    "Build an AI/ML profile, upload your CV, and get a ranked list of roles with an explained compatibility score and a prioritised skill-gap report.",
  keywords: ["career", "job recommendations", "AI", "machine learning", "skill gap", "CV analysis"],
  authors: [{ name: "CareerLens AI — SDP400, BUBT" }],
  openGraph: {
    title: "CareerLens AI",
    description: "AI-powered job and career recommendations for AI/ML roles.",
    type: "website",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0f172a",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <QueryProvider>
            <AuthProvider>
              {children}
              <Toaster />
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
