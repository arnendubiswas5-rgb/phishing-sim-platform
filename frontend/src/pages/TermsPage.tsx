import { LegalPage, Section } from "./LegalPage";

export function TermsPage() {
  return (
    <LegalPage title="Terms and Conditions" updated="October 2, 2026">
      <p>
        By using this platform you agree to the terms below. The platform provides tools to run phishing
        simulations for security-awareness training.
      </p>

      <Section heading="Authorized use only">
        <p>
          You may send simulations only to recipients your organization is authorized to test, such as your own
          employees or contractors under an agreed program. You are responsible for obtaining any consent or
          approval your jurisdiction and policies require.
        </p>
      </Section>

      <Section heading="Prohibited use">
        <p>
          You must not use the platform to deceive, harvest credentials from, or target anyone outside an
          authorized engagement, or for any unlawful purpose. Misuse may violate computer-misuse, wiretapping,
          and data-protection laws.
        </p>
      </Section>

      <Section heading="Your responsibilities">
        <p>
          You are responsible for the accuracy of the target lists you upload, for keeping account credentials
          and mail-relay secrets secure, and for configuring retention in line with your policies.
        </p>
      </Section>

      <Section heading="No warranty">
        <p>
          The platform is provided on an "as is" basis without warranties of any kind. Email deliverability and
          the behavior of third-party mail providers are outside the platform's control.
        </p>
      </Section>

      <Section heading="Limitation of liability">
        <p>
          To the maximum extent permitted by law, the operator is not liable for indirect or consequential
          damages arising from use of the platform.
        </p>
      </Section>

      <p className="text-xs text-neutral-500">
        This document is a starting template and should be reviewed by legal counsel before production use.
      </p>
    </LegalPage>
  );
}
