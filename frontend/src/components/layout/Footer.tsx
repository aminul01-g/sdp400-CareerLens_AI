/**
 * Site footer.
 *
 * Ported from the predecessor's `Footer.tsx`: `react-router-dom`'s `Link` becomes
 * `next/link`, and the "CareerGuide AI" branding is corrected to "CareerLens AI".
 */
import Link from "next/link";
import { Brain } from "lucide-react";

const productLinks = [
  { href: "/features", label: "Features" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/recommendations", label: "Recommendations" },
  { href: "/skill-gap", label: "Skill Gap" },
];

const resourceLinks = [
  { href: "/about", label: "About" },
  { href: "/feedback", label: "Feedback" },
  { href: "/register", label: "Create an account" },
];

export function Footer() {
  return (
    <footer className="border-t bg-muted/30">
      <div className="container mx-auto px-4 py-12">
        <div className="grid gap-8 md:grid-cols-4">
          <div className="space-y-3 md:col-span-2">
            <Link href="/" className="flex items-center gap-2 font-semibold">
              <Brain className="h-6 w-6 text-primary" aria-hidden="true" />
              <span>
                CareerLens <span className="text-primary">AI</span>
              </span>
            </Link>
            <p className="max-w-sm text-sm text-muted-foreground">
              An AI-powered job and career recommendation system for AI/ML roles. Build a
              profile, upload your CV, and get a ranked list of roles with an explained
              compatibility score and a prioritised skill-gap report.
            </p>
          </div>

          <nav className="space-y-3" aria-label="Product">
            <p className="text-sm font-semibold">Product</p>
            <ul className="space-y-2">
              {productLinks.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="text-sm text-muted-foreground hover:text-foreground">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          <nav className="space-y-3" aria-label="Resources">
            <p className="text-sm font-semibold">Resources</p>
            <ul className="space-y-2">
              {resourceLinks.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="text-sm text-muted-foreground hover:text-foreground">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>

        <div className="mt-8 flex flex-col gap-2 border-t pt-6 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} CareerLens AI — SDP400, BUBT.</p>
          <p>
            Built with Next.js, FastAPI, PostgreSQL, scikit-learn, and spaCy. The matching
            engine uses unsupervised similarity and rule-based weighting — no trained
            classifier.
          </p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
