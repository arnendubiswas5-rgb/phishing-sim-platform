import { LegalPage, Section } from "./LegalPage";

export function PrivacyPage() {
  return (
    <LegalPage title="Privacy Policy" updated="October 2, 2026">
      <p>
        This platform runs authorized phishing-simulation exercises for security-awareness training. It is
        operated by your organization for its own staff. This page explains what data the platform stores and
        how it is used.
      </p>

      <Section heading="Data we store">
        <p>
          Target records you upload (name, email address, department, and job title), the email templates and
          landing pages you create, and the events generated during a simulation (email sent, opened, link
          clicked, form submitted, and training completed).
        </p>
        <p>
          When a landing page is configured to capture credentials, submitted values are stored encrypted at
          rest so an operator can measure who entered data. They are kept only for the campaign's reporting and
          are removed by the retention schedule described below.
        </p>
      </Section>

      <Section heading="How we use it">
        <p>
          Data is used solely to run simulations, produce reports, and assign follow-up training. It is scoped
          to your organization and is not sold, rented, or shared with third parties.
        </p>
      </Section>

      <Section heading="Access">
        <p>
          Records are isolated per organization. Only users with an account in your organization can view them,
          and sensitive actions such as adding mail relays require an administrator role. Administrative actions
          are written to an audit log.
        </p>
      </Section>

      <Section heading="Retention">
        <p>
          Campaign and tracking data older than your configured retention period is deleted automatically by a
          daily job. Administrators can change the retention period or run the purge immediately from the
          settings page.
        </p>
      </Section>

      <Section heading="Contact">
        <p>
          For questions about this policy or a request relating to your data, contact your organization's
          security team or platform administrator.
        </p>
      </Section>

      <p className="text-xs text-neutral-500">
        This document is a starting template and should be reviewed by legal counsel before production use.
      </p>
    </LegalPage>
  );
}
