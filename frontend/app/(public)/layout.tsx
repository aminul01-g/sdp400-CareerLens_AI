/** Public shell: header + footer, no authentication requirement. */
import { Header } from "@/components/layout/Header";
import { SkipLink } from "@/components/shared/SkipLink";
import { Footer } from "@/components/layout/Footer";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <SkipLink />
      <Header />
      <main id="main-content" tabIndex={-1} className="flex-1">
        {children}
      </main>
      <Footer />
    </div>
  );
}
