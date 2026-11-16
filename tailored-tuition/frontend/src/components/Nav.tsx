"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useStudentContext } from "./StudentProvider";

const LINKS = [
  { href: "/learn", label: "Learn" },
  { href: "/progress", label: "Progress" },
];

export default function Nav() {
  const pathname = usePathname();
  const { student } = useStudentContext();

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-bg/90 backdrop-blur">
      <nav aria-label="Main" className="mx-auto flex h-14 max-w-4xl items-center gap-1 px-4">
        <Link href="/" className="mr-3 shrink-0 font-semibold text-fg">
          Tailored<span className="text-accent"> Tuition</span>
        </Link>
        {student?.persona &&
          LINKS.map((l) => {
            const active = pathname.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-md px-2.5 py-1.5 text-sm ${
                  active ? "bg-accent-soft font-medium text-fg" : "text-muted hover:text-fg"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        {student && (
          <span className="ml-auto truncate pl-2 text-sm text-muted" title={student.name}>
            {student.name}
          </span>
        )}
      </nav>
    </header>
  );
}
