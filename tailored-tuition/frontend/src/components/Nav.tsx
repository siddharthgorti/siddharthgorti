"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useAuth } from "./AuthProvider";

const STUDENT_LINKS = [
  { href: "/learn", label: "Learn" },
  { href: "/progress", label: "Progress" },
];
const GUARDIAN_LINKS = [
  { href: "/guardian", label: "Dashboard" },
  { href: "/privacy", label: "Privacy" },
];

export default function Nav() {
  const pathname = usePathname();
  const { me, logout } = useAuth();
  const [leaving, setLeaving] = useState(false);

  const links =
    me?.role === "student" ? (me.student.persona ? STUDENT_LINKS : []) : me?.role === "guardian" ? GUARDIAN_LINKS : [];
  const name = me?.role === "student" ? me.student.name : me?.role === "guardian" ? me.guardian.name : null;

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-bg/90 backdrop-blur">
      <nav aria-label="Main" className="mx-auto flex h-14 max-w-4xl items-center gap-1 px-4">
        <Link href="/" className="mr-2 shrink-0 font-semibold text-fg sm:mr-3" aria-label="Tailored Tuition home">
          <span className="sm:hidden">
            T<span className="text-accent">T</span>
          </span>
          <span className="hidden sm:inline">
            Tailored<span className="text-accent"> Tuition</span>
          </span>
        </Link>
        {links.map((l) => {
          const active = pathname.startsWith(l.href);
          return (
            <Link
              key={l.href}
              href={l.href}
              aria-current={active ? "page" : undefined}
              className={`shrink-0 rounded-md px-2 py-1.5 text-sm ${
                active ? "bg-accent-soft font-medium text-fg" : "text-muted hover:text-fg"
              }`}
            >
              {l.label}
            </Link>
          );
        })}
        <div className="ml-auto flex min-w-0 items-center gap-2 pl-1">
          {me && name && (
            <span className="min-w-0 max-w-[6rem] truncate text-sm text-muted sm:max-w-[10rem]" title={name}>
              {name}
            </span>
          )}
          {me ? (
            <button
              type="button"
              disabled={leaving}
              onClick={() => {
                setLeaving(true);
                void logout().finally(() => setLeaving(false));
              }}
              className="shrink-0 rounded-md border border-border px-2 py-1 text-sm text-muted hover:text-fg disabled:opacity-50"
            >
              Log out
            </button>
          ) : (
            me === null &&
            pathname !== "/login" && (
              <Link href="/login" className="shrink-0 rounded-md border border-border px-2 py-1 text-sm text-muted hover:text-fg">
                Log in
              </Link>
            )
          )}
        </div>
      </nav>
    </header>
  );
}
