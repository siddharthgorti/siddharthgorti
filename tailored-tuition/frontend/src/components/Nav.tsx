"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useStudentContext } from "./StudentProvider";

const LINKS = [
  { href: "/learn", label: "Learn" },
  { href: "/progress", label: "Progress" },
];

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const { student, signOut } = useStudentContext();

  // Lets someone else try the app on the same device (e.g. in-person demos).
  // Progress stays saved on the server; this device just stops remembering it.
  const startNewStudent = () => {
    if (!window.confirm(`Start as a new student? ${student?.name ?? "This student"}'s progress stays saved.`)) return;
    signOut();
    router.push("/");
  };

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
          <button
            type="button"
            onClick={startNewStudent}
            title="Start as a new student"
            aria-label={`Signed in as ${student.name}. Start as a new student`}
            className="ml-auto flex min-w-0 items-center gap-1.5 rounded-md border border-border px-2 py-1 text-sm text-muted hover:text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
          >
            <span className="max-w-[7rem] truncate">{student.name}</span>
            <span aria-hidden="true" className="shrink-0 text-xs">
              ⇄<span className="hidden sm:inline"> New student</span>
            </span>
          </button>
        )}
      </nav>
    </header>
  );
}
