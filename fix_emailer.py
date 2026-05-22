import os

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "emailer.js")

content = '''// emailer.js
// Sends email via SendGrid API (works on DigitalOcean — no SMTP port blocking)
// Falls back to Gmail SMTP if SENDGRID_API_KEY not set (for local Mac)

import { logger } from "./logger.js";

const SENDGRID_KEY = process.env.SENDGRID_API_KEY;
const EMAIL_TO = process.env.EMAIL_TO || process.env.EMAIL_USER;
const EMAIL_FROM = process.env.EMAIL_FROM || process.env.EMAIL_USER || "noreply@nazar-ai.com";

async function sendViaSendGrid(to, subject, html) {
  const response = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${SENDGRID_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: to }] }],
      from: { email: EMAIL_FROM, name: "Legal Account Tracker" },
      subject,
      content: [{ type: "text/html", value: html }],
    }),
  });
  if (!response.ok) {
    const err = await response.text();
    throw new Error(`SendGrid error ${response.status}: ${err}`);
  }
  return true;
}

async function sendViaGmail(to, subject, html) {
  const nodemailer = (await import("nodemailer")).default;
  const transporter = nodemailer.createTransport({
    host: process.env.EMAIL_HOST || "smtp.gmail.com",
    port: 587,
    secure: false,
    auth: { user: process.env.EMAIL_USER, pass: process.env.EMAIL_PASS },
  });
  await transporter.sendMail({ from: process.env.EMAIL_USER, to, subject, html });
  return true;
}

export async function sendEmail(to, subject, html) {
  const recipient = to || EMAIL_TO;
  if (!recipient) { logger.warn("No email recipient configured"); return false; }
  try {
    if (SENDGRID_KEY) {
      await sendViaSendGrid(recipient, subject, html);
      logger.info(`Email sent via SendGrid to ${recipient}: ${subject}`);
    } else {
      await sendViaGmail(recipient, subject, html);
      logger.info(`Email sent via Gmail to ${recipient}: ${subject}`);
    }
    return true;
  } catch(err) {
    logger.error(`Email failed`, { error: err.message });
    return false;
  }
}

export async function sendAccountNotification(account, changes, researchData) {
  const subject = `[Nazar] ${account.name} — ${changes.length} update(s)`;
  const html = `<div style="font-family:Arial,sans-serif;max-width:600px">
    <div style="background:#1B3A5C;padding:20px;border-radius:8px 8px 0 0">
      <h2 style="color:white;margin:0">${account.name}</h2>
      <p style="color:#aaa;margin:4px 0 0">${account.industry} · ${account.location}</p>
    </div>
    <div style="background:#f8f9fa;padding:20px;border-radius:0 0 8px 8px">
      <h3 style="color:#1B3A5C">What changed:</h3>
      <ul>${changes.map(c => `<li>${c}</li>`).join("")}</ul>
      ${researchData?.intel_summary ? `<p style="color:#555;font-style:italic">${researchData.intel_summary}</p>` : ""}
      <p><a href="https://nazar-ai.com" style="background:#2563A8;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">View Dashboard</a></p>
    </div>
  </div>`;
  return sendEmail(EMAIL_TO, subject, html);
}

export async function sendWeeklyDigest(digestData) {
  const subject = `[Nazar] Weekly Legal Intelligence Digest — ${new Date().toLocaleDateString("en-US", { month: "long", day: "numeric" })}`;
  const priorityHtml = (digestData.priority_accounts || []).slice(0, 5).map(a => `
    <div style="border:1px solid #e0e0e0;border-left:4px solid #2563A8;border-radius:6px;padding:14px;margin-bottom:12px">
      <div style="font-weight:bold;color:#1B3A5C">${a.account_name} <span style="font-size:12px;background:#EBF3FB;color:#2563A8;padding:2px 8px;border-radius:10px">${a.urgency}</span></div>
      <div style="color:#555;margin:6px 0;font-size:13px">${a.trigger}</div>
      <div style="color:#0E7C6E;font-size:13px"><strong>Action:</strong> ${a.action}</div>
    </div>`).join("");
  const html = `<div style="font-family:Arial,sans-serif;max-width:600px">
    <div style="background:#1B3A5C;padding:20px;border-radius:8px 8px 0 0">
      <h2 style="color:white;margin:0">Weekly Legal Intelligence Digest</h2>
      <p style="color:#aaa;margin:4px 0 0">${new Date().toLocaleDateString("en-US", { weekday:"long", year:"numeric", month:"long", day:"numeric" })}</p>
    </div>
    <div style="background:#f8f9fa;padding:20px;border-radius:0 0 8px 8px">
      ${digestData.week_summary ? `<p style="color:#333;font-size:14px;line-height:1.6">${digestData.week_summary}</p>` : ""}
      <h3 style="color:#1B3A5C">Priority accounts this week:</h3>
      ${priorityHtml}
      <p><a href="https://nazar-ai.com/digest" style="background:#2563A8;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">View Full Digest</a></p>
    </div>
  </div>`;
  return sendEmail(EMAIL_TO, subject, html);
}

export async function sendFilingsAlert(account, filings) {
  const subject = `[Nazar] New filing: ${account.name}`;
  const html = `<div style="font-family:Arial,sans-serif;max-width:600px">
    <div style="background:#B45309;padding:20px;border-radius:8px 8px 0 0">
      <h2 style="color:white;margin:0">New Filing Alert: ${account.name}</h2>
    </div>
    <div style="background:#f8f9fa;padding:20px;border-radius:0 0 8px 8px">
      ${filings.map(f => `<div style="border:1px solid #FDE68A;background:#FFFBF0;border-radius:6px;padding:12px;margin-bottom:8px">
        <div style="font-weight:bold;color:#B45309">${f.type} <span style="font-size:11px;color:#888">[${f.source}]</span></div>
        <div style="color:#555;font-size:13px;margin-top:4px">${f.summary}</div>
      </div>`).join("")}
      <p><a href="https://nazar-ai.com" style="background:#B45309;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">View Dashboard</a></p>
    </div>
  </div>`;
  return sendEmail(EMAIL_TO, subject, html);
}

export async function sendLitigationAlertEmail(alerts) {
  const subject = `[Nazar] Discovery phase alert — ${alerts.length} case(s)`;
  const html = `<div style="font-family:Arial,sans-serif;max-width:600px">
    <div style="background:#DC2626;padding:20px;border-radius:8px 8px 0 0">
      <h2 style="color:white;margin:0">Discovery Phase Alert</h2>
      <p style="color:#fca5a5;margin:4px 0 0">${alerts.length} case(s) entered discovery</p>
    </div>
    <div style="background:#f8f9fa;padding:20px;border-radius:0 0 8px 8px">
      ${alerts.map(a => `<div style="border:1px solid #FCA5A5;background:#FEF2F2;border-left:4px solid #DC2626;border-radius:6px;padding:14px;margin-bottom:12px">
        <div style="font-weight:bold;color:#1B3A5C">${a.account_name} — ${a.case_type}</div>
        <div style="color:#555;font-size:13px">Counsel: <strong>${a.outside_counsel || "TBD"}</strong></div>
        <div style="color:#0E7C6E;font-size:13px;margin-top:6px">${a.consilio_opportunity}</div>
      </div>`).join("")}
      <p><a href="https://nazar-ai.com" style="background:#DC2626;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">View Dashboard</a></p>
    </div>
  </div>`;
  return sendEmail(EMAIL_TO, subject, html);
}
'''

with open(path, 'w') as f:
    f.write(content)

print("Done — emailer.js written with SendGrid")
print("First line:", open(path).readline().strip())
