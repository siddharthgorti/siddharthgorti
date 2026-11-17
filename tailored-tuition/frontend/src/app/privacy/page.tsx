"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { PrivacyPolicy } from "@/lib/types";
import { Card } from "@/components/ui";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="space-y-2 text-sm leading-relaxed">{children}</div>
    </section>
  );
}

export default function PrivacyPage() {
  const [policy, setPolicy] = useState<PrivacyPolicy | null>(null);

  useEffect(() => {
    api.privacyPolicy().then(setPolicy).catch(() => setPolicy(null));
  }, []);

  return (
    <article className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Privacy notice</h1>
        <p className="text-sm text-muted">
          {policy ? `Version ${policy.version} · last updated ${policy.updated}` : "Plain-language summary of how we handle data."}
        </p>
      </div>

      <Card className="space-y-6">
        <Section title="Who we are">
          <p>
            Tailored Tuition is an AI maths tutor for CBSE Class 11 students. Contact:{" "}
            <em>[organisation name and contact email — to be filled in before launch]</em>.
          </p>
        </Section>

        <Section title="What we collect">
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <strong>About the parent or guardian:</strong> name, email address and a securely hashed password.
            </li>
            <li>
              <strong>About each child:</strong> first name, the username their guardian chose, and a securely hashed
              password.
            </li>
            <li>
              <strong>Learning activity:</strong> chat messages with the tutor, quiz answers, mastery levels per topic,
              and the tutor style the child chose.
            </li>
            <li>
              <strong>What we do not store:</strong> the personality-style scores from the five onboarding questions.
              They are shown once to help choose a tutor and then discarded.
            </li>
          </ul>
        </Section>

        <Section title="Why we use it">
          <p>
            Only to tutor the child and to show the child and their guardian how they are progressing. No
            advertising. We never sell data, and children&apos;s data is never shown to other students.
          </p>
        </Section>

        <Section title="AI processing">
          <p>
            To write the tutor&apos;s replies and quiz questions, the child&apos;s messages and the relevant syllabus text are
            sent to an AI model: either Anthropic&apos;s Claude (a cloud service) or a model running on the same computer as
            this app, depending on how it is set up.
          </p>
        </Section>

        <Section title="How long we keep it">
          <p>Until the guardian deletes it. Deleting a child or the guardian account removes the data permanently.</p>
        </Section>

        <Section title="Your choices and rights">
          <p>From the guardian dashboard, a parent or guardian can at any time:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>download all of a child&apos;s data as a file;</li>
            <li>permanently delete a child&apos;s data, which also withdraws consent;</li>
            <li>change a child&apos;s password, or delete their own account and all their children&apos;s data.</li>
          </ul>
        </Section>

        <Section title="Children">
          <p>
            Accounts for students under 18 are created only by a parent or legal guardian, who must verify their email
            address and give consent for each child. Students cannot sign up on their own.
          </p>
        </Section>
      </Card>
    </article>
  );
}
