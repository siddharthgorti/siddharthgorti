import type { Metadata, Viewport } from "next";
import "katex/dist/katex.min.css";
import "./globals.css";
import Nav from "@/components/Nav";
import { StudentProvider } from "@/components/StudentProvider";

export const metadata: Metadata = {
  title: "Tailored Tuition",
  description: "A patient, personal maths tutor for CBSE Class 11.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f7f6f2" },
    { media: "(prefers-color-scheme: dark)", color: "#14161a" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-dvh">
        <StudentProvider>
          <Nav />
          <main className="mx-auto w-full max-w-4xl px-4 py-6">{children}</main>
        </StudentProvider>
      </body>
    </html>
  );
}
