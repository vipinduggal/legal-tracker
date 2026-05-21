// emailer.js — Sends Outlook notifications via SMTP

import nodemailer from 'nodemailer';
import { logger } from './logger.js';
import { format } from 'date-fns';

let transporter = null;

function getTransporter() {
  if (transporter) return transporter;
  transporter = nodemailer.createTransport({
    host: process.env.EMAIL_HOST || 'smtp.office365.com',
    port: parseInt(process.env.EMAIL_PORT) || 587,
    secure: false,
    auth: {
      user: process.env.EMAIL_USER,
      pass: process.env.EMAIL_PASS,
    },
    tls: { ciphers: 'SSLv3' },
  });
  return transporter;
}

/**
 * Send a notification when a single account has been updated.
 */
export async function sendAccountUpdateEmail(account, changes, researchData) {
  if (!process.env.EMAIL_USER || !process.env.EMAIL_PASS) {
    logger.warn('Email not configured — skipping account update notification');
    return false;
  }

  const date = format(new Date(), 'MMMM d, yyyy');
  const activeIssues = [
    ...(researchData.litigation || []).filter(l => l.status !== 'Resolved' && l.status !== 'Settled'),
    ...(researchData.regulatory || []).filter(r => r.status !== 'Resolved' && r.status !== 'Closed'),
  ];

  const html = `
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: Segoe UI, Arial, sans-serif; font-size: 14px; color: #333; margin: 0; padding: 0; background: #f5f5f5; }
  .container { max-width: 600px; margin: 24px auto; background: white; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; }
  .header { background: #0078d4; color: white; padding: 20px 24px; }
  .header h1 { font-size: 18px; font-weight: 600; margin: 0 0 4px; }
  .header p { font-size: 13px; opacity: 0.85; margin: 0; }
  .body { padding: 20px 24px; }
  .change-list { background: #f0f7ff; border-left: 3px solid #0078d4; padding: 10px 14px; border-radius: 0 4px 4px 0; margin: 12px 0; }
  .change-list ul { margin: 0; padding-left: 16px; }
  .change-list li { font-size: 13px; margin: 4px 0; color: #1a1a1a; }
  .section { margin: 16px 0; }
  .section h3 { font-size: 13px; font-weight: 600; color: #555; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
  .contact-row { display: flex; gap: 8px; align-items: baseline; padding: 4px 0; border-bottom: 1px solid #f0f0f0; }
  .tag { font-size: 11px; padding: 1px 6px; border-radius: 10px; background: #e8f0fe; color: #1a73e8; font-weight: 500; }
  .pill-amber { background: #fef3e2; color: #b45309; }
  .pill-red { background: #fee2e2; color: #991b1b; }
  .intel-box { background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 12px; margin-top: 12px; font-size: 13px; line-height: 1.6; }
  .footer { padding: 12px 24px; background: #f9f9f9; font-size: 11px; color: #888; border-top: 1px solid #eee; }
  .cta { display: inline-block; margin-top: 14px; padding: 8px 16px; background: #0078d4; color: white; border-radius: 4px; text-decoration: none; font-size: 13px; font-weight: 500; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📋 ${account.name} — Research Updated</h1>
    <p>${date} · Legal Account Tracker</p>
  </div>
  <div class="body">
    <p style="font-size:14px;margin-bottom:12px">Research has been refreshed for <strong>${account.name}</strong> (${account.industry}).</p>

    <div class="change-list">
      <strong style="font-size:12px;color:#0078d4">WHAT CHANGED</strong>
      <ul>
        ${changes.map(c => `<li>${c}</li>`).join('')}
      </ul>
    </div>

    ${researchData.contacts?.length ? `
    <div class="section">
      <h3>Key contacts (${researchData.contacts.length})</h3>
      ${researchData.contacts.slice(0, 5).map(c => `
        <div class="contact-row">
          <span class="tag">${c.tag}</span>
          <strong style="font-size:13px">${c.name}</strong>
          <span style="font-size:12px;color:#666">${c.title}</span>
        </div>`).join('')}
    </div>` : ''}

    ${activeIssues.length ? `
    <div class="section">
      <h3>Active legal issues (${activeIssues.length})</h3>
      ${activeIssues.slice(0, 4).map(i => `
        <div style="padding:6px 0;border-bottom:1px solid #f0f0f0;font-size:13px">
          <span class="tag pill-amber">${i.status}</span>
          <strong style="margin-left:6px">${i.type}</strong>
          ${i.counsel ? `<span style="color:#666;font-size:12px"> · ${i.counsel}</span>` : ''}
        </div>`).join('')}
    </div>` : ''}

    ${researchData.intel_summary ? `
    <div class="intel-box">
      <strong style="font-size:12px;color:#92400e">💡 SALES INTEL</strong><br>
      ${researchData.intel_summary}
    </div>` : ''}
  </div>
  <div class="footer">
    Legal Account Tracker · Automated daily research · Reply to this email with any corrections
  </div>
</div>
</body>
</html>`;

  try {
    await getTransporter().sendMail({
      from: `"Legal Tracker" <${process.env.EMAIL_FROM}>`,
      to: process.env.EMAIL_TO,
      subject: `[Tracker] ${account.name} updated — ${changes[0]}`,
      html,
    });
    logger.info(`Email sent for ${account.name}`);
    return true;
  } catch (err) {
    logger.error(`Email failed for ${account.name}`, { error: err.message });
    return false;
  }
}

/**
 * Send the weekly outreach digest email.
 */
export async function sendWeeklyDigestEmail(digest) {
  if (!process.env.EMAIL_USER || !process.env.EMAIL_PASS) {
    logger.warn('Email not configured — skipping digest');
    return false;
  }

  const date = format(new Date(), 'MMMM d, yyyy');
  const priorities = digest.priority_accounts || [];
  const quick = digest.quick_touches || [];

  const html = `
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: Segoe UI, Arial, sans-serif; font-size: 14px; color: #333; margin: 0; padding: 0; background: #f5f5f5; }
  .container { max-width: 650px; margin: 24px auto; background: white; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; }
  .header { background: #107c10; color: white; padding: 20px 24px; }
  .header h1 { font-size: 18px; font-weight: 600; margin: 0 0 4px; }
  .header p { font-size: 13px; opacity: 0.85; margin: 0; }
  .body { padding: 20px 24px; }
  .week-summary { background: #f0fdf4; border-left: 3px solid #107c10; padding: 10px 14px; border-radius: 0 4px 4px 0; margin-bottom: 20px; font-size: 13px; line-height: 1.6; }
  .account-card { border: 1px solid #e8e8e8; border-radius: 8px; padding: 16px; margin-bottom: 14px; }
  .account-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
  .rank-badge { width: 24px; height: 24px; border-radius: 50%; background: #107c10; color: white; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; float: left; margin-right: 8px; }
  .account-name { font-size: 15px; font-weight: 600; }
  .reason-text { font-size: 12px; color: #555; margin-bottom: 10px; line-height: 1.5; padding-left: 32px; }
  .contact-chip { display: inline-block; background: #e8f0fe; color: #1a73e8; border-radius: 4px; padding: 2px 8px; font-size: 12px; margin-bottom: 8px; }
  .talking-point { font-size: 13px; font-style: italic; color: #444; background: #fafafa; border: 1px solid #eee; border-radius: 4px; padding: 8px 10px; margin-bottom: 10px; }
  .email-block { background: #f8f8f8; border-radius: 6px; padding: 12px; font-size: 12px; line-height: 1.6; border: 1px solid #eee; }
  .email-subject { font-weight: 600; font-size: 13px; margin-bottom: 6px; color: #000; }
  .quick-list { background: #fff8e1; border-radius: 6px; padding: 12px 16px; }
  .quick-list li { font-size: 13px; margin: 5px 0; }
  .section-title { font-size: 12px; font-weight: 700; color: #666; text-transform: uppercase; letter-spacing: 0.05em; margin: 20px 0 10px; border-bottom: 1px solid #eee; padding-bottom: 6px; }
  .footer { padding: 12px 24px; background: #f9f9f9; font-size: 11px; color: #888; border-top: 1px solid #eee; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📬 Weekly Outreach Digest</h1>
    <p>Week of ${date} · Legal Account Tracker</p>
  </div>
  <div class="body">

    ${digest.week_summary ? `
    <div class="week-summary">
      <strong style="font-size:11px;color:#166534;text-transform:uppercase;letter-spacing:.05em">This week's themes</strong><br>
      ${digest.week_summary}
    </div>` : ''}

    <div class="section-title">Priority outreach — top ${priorities.length} accounts</div>

    ${priorities.map((p, i) => `
    <div class="account-card">
      <div>
        <span class="rank-badge" style="display:inline-flex;width:22px;height:22px;border-radius:50%;background:#107c10;color:white;font-size:11px;font-weight:700;align-items:center;justify-content:center;margin-right:8px">${i + 1}</span>
        <strong class="account-name">${p.account_name}</strong>
      </div>
      <div class="reason-text">${p.reason}</div>
      ${p.contact ? `<div><span class="contact-chip">→ ${p.contact.name} · ${p.contact.title}</span><span style="font-size:11px;color:#666;margin-left:6px">${p.contact.why_them}</span></div>` : ''}
      ${p.talking_point ? `<div class="talking-point" style="margin-top:8px">"${p.talking_point}"</div>` : ''}
      ${p.email ? `
      <div class="email-block">
        <div class="email-subject">Subject: ${p.email.subject}</div>
        <div style="white-space:pre-line">${p.email.body}</div>
      </div>` : ''}
      ${p.linkedin_message ? `<div style="margin-top:8px;font-size:12px;color:#555"><strong>LinkedIn:</strong> ${p.linkedin_message}</div>` : ''}
    </div>`).join('')}

    ${quick.length ? `
    <div class="section-title">Quick touches</div>
    <div class="quick-list">
      <ul style="margin:0;padding-left:16px">
        ${quick.map(q => `<li><strong>${q.account_name}:</strong> ${q.action}</li>`).join('')}
      </ul>
    </div>` : ''}

  </div>
  <div class="footer">
    Legal Account Tracker · Weekly digest every Monday · Auto-generated from daily research
  </div>
</div>
</body>
</html>`;

  try {
    await getTransporter().sendMail({
      from: `"Legal Tracker" <${process.env.EMAIL_FROM}>`,
      to: process.env.EMAIL_TO,
      subject: `[Tracker] Weekly outreach digest — ${date} — ${priorities.length} priority accounts`,
      html,
    });
    logger.info('Weekly digest email sent');
    return true;
  } catch (err) {
    logger.error('Weekly digest email failed', { error: err.message });
    return false;
  }
}


/**
 * Send an immediate alert when new filings are detected.
 */
export async function sendFilingsAlertEmail(account, newFilings) {
  if (!process.env.EMAIL_USER || !process.env.EMAIL_PASS) {
    return false;
  }

  const date = new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });

  const html = `
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body{font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#333;margin:0;padding:0;background:#f5f5f5}
  .container{max-width:600px;margin:24px auto;background:white;border-radius:8px;overflow:hidden;border:1px solid #e0e0e0}
  .header{background:#991B1B;color:white;padding:20px 24px}
  .header h1{font-size:18px;font-weight:600;margin:0 0 4px}
  .header p{font-size:13px;opacity:.85;margin:0}
  .body{padding:20px 24px}
  .filing-card{border:1px solid #FEE2E2;border-left:4px solid #991B1B;border-radius:4px;padding:12px;margin:10px 0;background:#FFF5F5}
  .filing-type{font-size:14px;font-weight:600;color:#991B1B;margin-bottom:4px}
  .filing-summary{font-size:13px;color:#333;margin-bottom:8px;line-height:1.5}
  .action-box{background:#FEF3C7;border:1px solid #FDE68A;border-radius:4px;padding:10px;font-size:13px;color:#92400E}
  .action-label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px;color:#B45309}
  .footer{padding:12px 24px;background:#f9f9f9;font-size:11px;color:#888;border-top:1px solid #eee}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🚨 New Filing Alert — ${account.name}</h1>
    <p>${date} · Legal Account Tracker · Immediate notification</p>
  </div>
  <div class="body">
    <p style="margin-bottom:14px;font-size:14px">${newFilings.length} new filing${newFilings.length > 1 ? "s" : ""} detected for <strong>${account.name}</strong> (${account.industry}) in the last 30 days.</p>
    ${newFilings.map(f => `
    <div class="filing-card">
      <div class="filing-type">${f.type}</div>
      <div class="filing-summary">${f.summary}</div>
      ${f.counsel ? `<div style="font-size:12px;color:#666;margin-bottom:8px">Outside counsel: <strong>${f.counsel}</strong></div>` : ""}
      ${f.suggested_action ? `
      <div class="action-box">
        <div class="action-label">💡 Suggested action this week</div>
        ${f.suggested_action}
      </div>` : ""}
    </div>`).join("")}
  </div>
  <div class="footer">Legal Account Tracker · New filing alerts · Automated daily monitoring</div>
</div>
</body>
</html>`;

  try {
    await getTransporter().sendMail({
      from: `"Legal Tracker" <${process.env.EMAIL_FROM}>`,
      to: process.env.EMAIL_TO,
      subject: `[ALERT] New filing — ${account.name}: ${newFilings[0]?.type}`,
      html,
    });
    logger.info("Filing alert email sent for " + account.name);
    return true;
  } catch (err) {
    logger.error("Filing alert email failed for " + account.name, { error: err.message });
    return false;
  }
}
