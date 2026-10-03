#!/usr/bin/env python3
"""Seeds a self-contained set of local test/demo data: a tenant, an admin
user, a target group with 3 dummy targets, a fake-SSO phishing template, a
credential-harvesting landing page, an SMTP profile pointing at a local
Mailpit instance, and a campaign that gets launched immediately so the email
lands in Mailpit for inspection.

Safe to re-run: every step is get-or-create, so running this again reuses
existing rows instead of duplicating them. The campaign only actually
launches once - if it's already past DRAFT status from a previous run, this
script reports its status instead of dispatching a second time.

Run from inside the backend container (so `mailpit`/the DB resolve via the
docker-compose network, and the `app` package is on the path the same way it
is for the API and worker):

    docker compose exec backend python scripts/seed_test_data.py

Or locally from the backend/ directory against the same DATABASE_URL the
containers use (in which case the SMTP profile's host="mailpit" only works if
something resolves that name - e.g. add "127.0.0.1 mailpit" to your hosts
file, or edit SMTP_HOST below to "localhost" if you're not running in Docker).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.campaign import Campaign, CampaignStatus, CampaignTarget, CampaignType
from app.models.group import TargetGroup
from app.models.page import Page
from app.models.smtp_profile import SmtpProfile
from app.models.target import Target
from app.models.template import Template
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.utils.security import hash_password
from app.utils.tracking import generate_tracking_signature, generate_tracking_uuid
from app.workers.email_worker import dispatch_campaign

TENANT_NAME = "Test Lab"
TENANT_SLUG = "test-lab"
ADMIN_EMAIL = "admin@test-lab.local"
ADMIN_PASSWORD = "TestAdmin_123!"
GROUP_NAME = "QA Test Targets"
TEMPLATE_NAME = "Fake SSO Login Alert"
PAGE_NAME = "Fake SSO Credential Harvest"
SMTP_PROFILE_NAME = "Local Mailpit"
CAMPAIGN_NAME = "QA Test Campaign"

# Reserved for documentation/examples per RFC 2606 - never a real domain.
SENDER_EMAIL = "sso-alerts@corp-lookalike.test"
SMTP_HOST = "mailpit"  # docker-compose service name; see module docstring
SMTP_PORT = 1025

DUMMY_TARGETS = [
    {
        "email": "test1@lab.local", "first_name": "Test", "last_name": "One",
        "department": "Engineering", "position": "Software Engineer",
    },
    {
        "email": "test2@lab.local", "first_name": "Test", "last_name": "Two",
        "department": "Finance", "position": "Accountant",
    },
    {
        "email": "test3@lab.local", "first_name": "Test", "last_name": "Three",
        "department": "Human Resources", "position": "Recruiter",
    },
]

# Deliberately uses the same urgency/verify-now pressure the education page
# (from a couple of prompts back) explicitly warns people to watch for.
TEMPLATE_HTML_BODY = """\
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #1a1a2e;">
  <p>Hi {{ first_name }},</p>
  <p>We detected unusual sign-in activity on your Single Sign-On (SSO) account. To keep your
  account secure, please verify your identity <strong>immediately</strong>.</p>
  <p style="text-align: center; margin: 32px 0;">
    <a href="{{ short_url }}"
       style="background:#0b5fff; color:#fff; padding:12px 28px; text-decoration:none;
              border-radius:6px; display:inline-block; font-weight:bold;">
      Verify My Account
    </a>
  </p>
  <p>If you do not verify within 24 hours, your account access will be temporarily suspended.</p>
  <p>Thank you,<br>IT Security Team</p>
  <img src="{{ tracking_pixel }}" width="1" height="1" style="display:none;" alt="">
</div>
"""

TEMPLATE_TEXT_BODY = """\
Hi {{ first_name }},

We detected unusual sign-in activity on your Single Sign-On (SSO) account. To keep your account
secure, please verify your identity immediately:

{{ short_url }}

If you do not verify within 24 hours, your account access will be temporarily suspended.

Thank you,
IT Security Team
"""

PAGE_HTML_CONTENT = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Single Sign-On</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f4f5f7; display: flex; align-items: center;
           justify-content: center; height: 100vh; margin: 0; }
    .card { background: #fff; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,.1);
            width: 320px; }
    input { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ccc; border-radius: 4px;
            box-sizing: border-box; }
    input[readonly] { background: #f1f3f5; color: #555; }
    .logo { display: block; max-height: 48px; margin: 0 auto 16px; }
    button { width: 100%; padding: 10px; background: #0b5fff; color: #fff; border: none;
             border-radius: 4px; cursor: pointer; font-weight: bold; }
  </style>
</head>
<body>
  <div class="card">
    {% if logo_url %}<img class="logo" src="{{ logo_url }}" alt="">{% endif %}
    <h2>Sign in to continue</h2>
    <p>Hi {{ first_name }}, please re-authenticate to verify your identity.</p>
    <form method="post" action="{{ submit_url }}">
      <input type="email" name="username" value="{{ email }}" readonly>
      <input type="password" name="password" placeholder="Password" required>
      <button type="submit">Sign In</button>
    </form>
  </div>
</body>
</html>
"""


async def _get_or_create_tenant(db: AsyncSession) -> Tenant:
    tenant = (await db.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))).scalar_one_or_none()
    if tenant is not None:
        print(f"[SKIP] Tenant '{TENANT_NAME}' already exists (id={tenant.id})")
        return tenant
    tenant = Tenant(name=TENANT_NAME, slug=TENANT_SLUG)
    db.add(tenant)
    await db.flush()
    print(f"[OK] Created tenant id={tenant.id} name='{TENANT_NAME}'")
    return tenant


async def _get_or_create_admin(db: AsyncSession, tenant: Tenant) -> User:
    user = (
        await db.execute(select(User).where(User.tenant_id == tenant.id, User.email == ADMIN_EMAIL))
    ).scalar_one_or_none()
    if user is not None:
        print(f"[SKIP] User '{ADMIN_EMAIL}' already exists (id={user.id})")
        return user
    user = User(
        tenant_id=tenant.id,
        email=ADMIN_EMAIL,
        hashed_password=hash_password(ADMIN_PASSWORD),
        full_name="Test Lab Admin",
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.flush()
    print(f"[OK] Created user id={user.id} name='{ADMIN_EMAIL}' (password: {ADMIN_PASSWORD})")
    return user


async def _get_or_create_group_with_targets(db: AsyncSession, tenant: Tenant) -> TargetGroup:
    group = (
        await db.execute(
            select(TargetGroup).where(TargetGroup.tenant_id == tenant.id, TargetGroup.name == GROUP_NAME)
        )
    ).scalar_one_or_none()
    if group is None:
        group = TargetGroup(tenant_id=tenant.id, name=GROUP_NAME, description="Dummy targets for local QA/testing")
        db.add(group)
        await db.flush()
        print(f"[OK] Created target_group id={group.id} name='{GROUP_NAME}'")
    else:
        print(f"[SKIP] Target group '{GROUP_NAME}' already exists (id={group.id})")

    existing_emails = set(
        (await db.execute(select(Target.email).where(Target.group_id == group.id))).scalars().all()
    )
    for data in DUMMY_TARGETS:
        if data["email"] in existing_emails:
            print(f"[SKIP] Target '{data['email']}' already exists")
            continue
        target = Target(group_id=group.id, **data)
        db.add(target)
        await db.flush()
        print(f"[OK] Created target id={target.id} name='{data['email']}'")
    return group


async def _get_or_create_template(db: AsyncSession, tenant: Tenant) -> Template:
    template = (
        await db.execute(select(Template).where(Template.tenant_id == tenant.id, Template.name == TEMPLATE_NAME))
    ).scalar_one_or_none()
    if template is not None:
        print(f"[SKIP] Template '{TEMPLATE_NAME}' already exists (id={template.id})")
        return template
    template = Template(
        tenant_id=tenant.id,
        name=TEMPLATE_NAME,
        subject="Action Required: Verify Your SSO Login",
        html_body=TEMPLATE_HTML_BODY,
        text_body=TEMPLATE_TEXT_BODY,
        sender_name="IT Security Team",
        sender_email=SENDER_EMAIL,
    )
    db.add(template)
    await db.flush()
    print(f"[OK] Created template id={template.id} name='{TEMPLATE_NAME}'")
    return template


async def _get_or_create_page(db: AsyncSession, tenant: Tenant) -> Page:
    page = (
        await db.execute(select(Page).where(Page.tenant_id == tenant.id, Page.name == PAGE_NAME))
    ).scalar_one_or_none()
    if page is not None:
        print(f"[SKIP] Page '{PAGE_NAME}' already exists (id={page.id})")
        return page
    page = Page(
        tenant_id=tenant.id,
        name=PAGE_NAME,
        html_content=PAGE_HTML_CONTENT,
        capture_credentials=True,
        redirect_url=None,
    )
    db.add(page)
    await db.flush()
    print(f"[OK] Created page id={page.id} name='{PAGE_NAME}'")
    return page


async def _get_or_create_smtp_profile(db: AsyncSession, tenant: Tenant) -> SmtpProfile:
    profile = (
        await db.execute(
            select(SmtpProfile).where(SmtpProfile.tenant_id == tenant.id, SmtpProfile.name == SMTP_PROFILE_NAME)
        )
    ).scalar_one_or_none()
    if profile is not None:
        print(f"[SKIP] SMTP profile '{SMTP_PROFILE_NAME}' already exists (id={profile.id})")
        return profile
    profile = SmtpProfile(
        tenant_id=tenant.id,
        name=SMTP_PROFILE_NAME,
        host=SMTP_HOST,
        port=SMTP_PORT,
        username=None,
        password_encrypted=None,  # Mailpit accepts unauthenticated SMTP by default
        use_tls=False,
        from_name="IT Security Team",
        from_email=SENDER_EMAIL,
    )
    db.add(profile)
    await db.flush()
    print(f"[OK] Created smtp_profile id={profile.id} name='{SMTP_PROFILE_NAME}' ({SMTP_HOST}:{SMTP_PORT})")
    return profile


async def _get_or_create_campaign(
    db: AsyncSession, tenant: Tenant, admin: User, template: Template, page: Page,
    smtp_profile: SmtpProfile, group: TargetGroup,
) -> tuple[Campaign, bool]:
    """Returns (campaign, should_launch). should_launch is only True the first
    time the campaign is created with DRAFT status still unlaunched."""
    campaign = (
        await db.execute(select(Campaign).where(Campaign.tenant_id == tenant.id, Campaign.name == CAMPAIGN_NAME))
    ).scalar_one_or_none()

    if campaign is not None:
        print(f"[SKIP] Campaign '{CAMPAIGN_NAME}' already exists (id={campaign.id}, status={campaign.status.value})")
        if campaign.status != CampaignStatus.DRAFT:
            return campaign, False
        # Exists but never actually launched (e.g. a prior run failed before
        # reaching that step) - fall through and launch it now.
    else:
        targets = (await db.execute(select(Target).where(Target.group_id == group.id))).scalars().all()
        campaign = Campaign(
            tenant_id=tenant.id,
            name=CAMPAIGN_NAME,
            template_id=template.id,
            page_id=page.id,
            smtp_profile_id=smtp_profile.id,
            campaign_type=CampaignType.CREDENTIAL_HARVEST,
            created_by=admin.id,
        )
        for target in targets:
            tracking_uuid = generate_tracking_uuid()
            campaign.recipients.append(
                CampaignTarget(
                    target_id=target.id,
                    tracking_uuid=tracking_uuid,
                    tracking_sig=generate_tracking_signature(tracking_uuid),
                )
            )
        db.add(campaign)
        await db.flush()
        print(f"[OK] Created campaign id={campaign.id} name='{CAMPAIGN_NAME}' ({len(targets)} recipient(s))")

    campaign.status = CampaignStatus.RUNNING
    print("  marking campaign RUNNING")
    return campaign, True


async def _print_summary(db: AsyncSession, tenant: Tenant) -> None:
    """Counts the rows that belong to this tenant and prints a summary table,
    so it's obvious at a glance whether any step above failed silently."""
    async def count(stmt) -> int:
        return (await db.execute(stmt)).scalar_one()

    templates = await count(select(func.count()).select_from(Template).where(Template.tenant_id == tenant.id))
    pages = await count(select(func.count()).select_from(Page).where(Page.tenant_id == tenant.id))
    smtp_profiles = await count(select(func.count()).select_from(SmtpProfile).where(SmtpProfile.tenant_id == tenant.id))
    campaigns = await count(select(func.count()).select_from(Campaign).where(Campaign.tenant_id == tenant.id))
    # Targets have no tenant_id of their own; they belong to the tenant's groups.
    targets = await count(
        select(func.count())
        .select_from(Target)
        .join(TargetGroup, Target.group_id == TargetGroup.id)
        .where(TargetGroup.tenant_id == tenant.id)
    )

    print("\n=== Summary (tenant '%s') ===" % tenant.name)
    for label, n in (
        ("templates", templates),
        ("pages", pages),
        ("smtp_profiles", smtp_profiles),
        ("campaigns", campaigns),
        ("targets", targets),
    ):
        print(f"  {label}={n}")


async def seed() -> tuple[str, bool]:
    async with AsyncSessionLocal() as db:
        print("1. Tenant + admin user")
        tenant = await _get_or_create_tenant(db)
        admin = await _get_or_create_admin(db, tenant)

        print("2. Target group + dummy targets")
        group = await _get_or_create_group_with_targets(db, tenant)

        print("3. Phishing template (fake SSO login)")
        template = await _get_or_create_template(db, tenant)

        print("4. Landing page (credential harvest)")
        page = await _get_or_create_page(db, tenant)

        print("5. SMTP profile (local Mailpit)")
        smtp_profile = await _get_or_create_smtp_profile(db, tenant)

        print("6. Campaign")
        campaign, should_launch = await _get_or_create_campaign(
            db, tenant, admin, template, page, smtp_profile, group
        )

        await db.commit()
        await _print_summary(db, tenant)
        return str(campaign.id), should_launch


def main() -> None:
    campaign_id, should_launch = asyncio.run(seed())

    if not should_launch:
        print("\nCampaign was already launched in a previous run - not sending again.")
    else:
        print("\n7. Launching campaign")
        # .apply() runs the task body synchronously, in-process, bypassing the
        # broker entirely - verified empirically that this works with no
        # Redis/celery_worker reachable at all, which keeps this script
        # self-contained instead of depending on a separate worker's health.
        result = dispatch_campaign.apply(args=[campaign_id])
        print("  dispatch result:", result.get())

    print(f"\nDone. Open Mailpit at http://localhost:8025 to see the sent email(s).")
    print(f"Log in to the platform with: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    main()
