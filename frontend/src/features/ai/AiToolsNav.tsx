"use client";

/**
 * The AI tools' sub-navigation.
 *
 * The main header already carries ten links and swaps them for the admin
 * links on the wide layout, so five more would have broken it. The AI
 * features therefore get their own navigation, which appears on every AI
 * screen and nowhere else. It is a plain list of links rather than a tab
 * component so that each one is a real URL: a learner can bookmark the job
 * analyser, and the browser's back button works.
 */
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, ClipboardList, FileSearch, MessagesSquare, Route } from "lucide-react";

import { cn } from "@/lib/utils";

const links = [
  { href: "/mentor", label: "Mentor", icon: MessagesSquare },
  { href: "/roadmaps", label: "Roadmaps", icon: Route },
  { href: "/job-analysis", label: "Job analysis", icon: FileSearch },
  { href: "/interview", label: "Interview", icon: ClipboardList },
  { href: "/resume/advice", label: "CV advice", icon: Bot },
] as const;

export function AiToolsNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="AI tools" className="border-b">
      <ul className="-mb-px flex flex-wrap gap-1">
        {links.map((link) => {
          const Icon = link.icon;
          const isActive =
            pathname === link.href || pathname.startsWith(`${link.href}/`);
          return (
            <li key={link.href}>
              <Link
                href={link.href}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "inline-flex items-center gap-2 whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {link.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
