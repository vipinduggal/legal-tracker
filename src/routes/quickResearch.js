// quickResearch.js
// On-demand research for any company — no account list required
// POST /api/quick-research { company: "Company Name", email: true/false }

import express from "express";
import Anthropic from "@anthropic-ai/sdk";
import { sendEmail } from "../emailer.js";
import { logger } from "../logger.js";

const router = express.Router();
const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

// Use Perplexity for live research
async function perplexitySearch(query) {
  const response = await fetch("https://api.perplexity.ai/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${process.env.PERPLEXITY_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "llama-3.1-sonar-large-128k-online",
      messages: [{ role: "user", content: query }],
      max_tokens: 2000,
    }),
  });
  const data = await response.json();
  return data.choices?.[0]?.message?.content || "";
}

router.post("/", async (req, res) => {
  const { company, sendEmailReport } = req.body;
  if (!company || company.trim().length < 2) {
    return res.status(400).json({ error: "Company name required" });
  }

  const companyName = company.trim();
  logger.info(`Quick research requested for: ${companyName}`);

  // Stream progress back via SSE — not needed here, just return JSON
  try {
    // Run 4 parallel Perplexity searches
    const [litigationRaw, financialRaw, contactsRaw, newsRaw] = await Promise.all([
      perplexitySearch(`Current litigation, lawsuits, regulatory actions involving ${companyName} legal department 2024 2025 2026. Include case names, courts, outside counsel if known.`),
      perplexitySearch(`${companyName} financial news, revenue, budget, M&A activity, layoffs, restructuring 2025 2026`),
      perplexitySearch(`${companyName} General Counsel, Chief Legal Officer, Head of Litigation, Head of Legal Operations, Deputy GC name title 2025 2026`),
      perplexitySearch(`${companyName} latest news, announcements, strategic developments May 2026`),
    ]);

    // Claude synthesizes into structured output
    const prompt = `You are a legal sales intelligence analyst. Synthesize this research on ${companyName} into a structured briefing for a Consilio eDiscovery sales rep.

LITIGATION DATA:
${litigationRaw}

FINANCIAL DATA:
${financialRaw}

CONTACTS DATA:
${contactsRaw}

RECENT NEWS:
${newsRaw}

Return a JSON object with this exact structure:
{
  "company": "${companyName}",
  "research_date": "${new Date().toISOString().split('T')[0]}",
  "executive_summary": "2-3 sentence overview of eDiscovery opportunity",
  "contacts": [
    {"name": "string", "title": "string", "confidence": "High|Medium|Low"}
  ],
  "litigation": [
    {"type": "string", "summary": "string", "status": "string", "outside_counsel": "string or null"}
  ],
  "financial_signals": ["string array of relevant financial signals"],
  "immediate_triggers": [
    {"trigger": "string", "urgency": "High|Medium|Low", "action": "string"}
  ],
  "strategic_notes": "string — longer term opportunity notes",
  "ediscovery_opportunity": "High|Medium|Low|Unknown"
}

Return JSON only. No markdown fences.`;

    const response = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 2000,
      messages: [{ role: "user", content: prompt }],
    });

    const raw = response.content.filter(b => b.type === "text").map(b => b.text).join("").trim();
    let result;
    try {
      result = JSON.parse(raw);
    } catch(e) {
      // Try to extract JSON
      const start = raw.indexOf("{");
      const end = raw.lastIndexOf("}");
      if (start > -1 && end > start) {
        result = JSON.parse(raw.slice(start, end + 1));
      } else {
        throw new Error("Could not parse Claude response as JSON");
      }
    }

    // Send email if requested
    if (sendEmailReport && process.env.EMAIL_TO) {
      const emailHtml = buildQuickResearchEmail(result);
      await sendEmail(
        process.env.EMAIL_TO,
        `[Nazar] Quick Research: ${companyName}`,
        emailHtml
      );
      logger.info(`Quick research email sent for ${companyName}`);
    }

    logger.info(`Quick research complete for ${companyName}`);
    return res.json({ success: true, data: result });

  } catch(err) {
    logger.error(`Quick research failed for ${companyName}`, { error: err.message });
    return res.status(500).json({ error: err.message });
  }
});

function buildQuickResearchEmail(data) {
  const urgencyColor = data.ediscovery_opportunity === "High" ? "#DC2626" :
                       data.ediscovery_opportunity === "Medium" ? "#D97706" : "#059669";

  const contactsHtml = (data.contacts || []).map(c =>
    `<tr><td style="padding:8px 12px;border-bottom:1px solid #f0f0f0">${c.name}</td>
     <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;color:#555">${c.title}</td>
     <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;color:#888;font-size:12px">${c.confidence}</td></tr>`
  ).join("");

  const litHtml = (data.litigation || []).map(l =>
    `<div style="border-left:3px solid #DC2626;padding:10px 14px;margin-bottom:10px;background:#FEF2F2;border-radius:0 6px 6px 0">
      <div style="font-weight:600;font-size:14px">${l.type}</div>
      <div style="color:#555;font-size:13px;margin-top:4px">${l.summary}</div>
      ${l.outside_counsel ? `<div style="color:#888;font-size:12px;margin-top:4px">Counsel: ${l.outside_counsel}</div>` : ""}
    </div>`
  ).join("");

  const triggersHtml = (data.immediate_triggers || []).map(t =>
    `<div style="border:1px solid #e0e0e0;border-radius:6px;padding:12px 14px;margin-bottom:10px">
      <div style="font-weight:600;font-size:13px;color:#1B3A5C">${t.trigger}</div>
      <div style="color:#0E7C6E;font-size:12px;margin-top:4px">→ ${t.action}</div>
    </div>`
  ).join("");

  return `<div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto">
    <div style="background:#1B3A5C;padding:24px;border-radius:8px 8px 0 0">
      <div style="font-size:11px;color:#aaa;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px">Quick Research Report</div>
      <h1 style="color:white;margin:0;font-size:24px">${data.company}</h1>
      <div style="margin-top:8px">
        <span style="background:${urgencyColor};color:white;font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px">
          ${data.ediscovery_opportunity} eDiscovery Opportunity
        </span>
      </div>
    </div>
    <div style="background:#f8f9fa;padding:24px;border-radius:0 0 8px 8px">
      <p style="color:#333;font-size:15px;line-height:1.7;margin-bottom:24px">${data.executive_summary}</p>
      
      ${data.contacts?.length ? `
      <h3 style="color:#1B3A5C;font-size:14px;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Key Contacts</h3>
      <table style="width:100%;border-collapse:collapse;margin-bottom:24px;background:white;border-radius:6px;overflow:hidden">
        ${contactsHtml}
      </table>` : ""}

      ${data.litigation?.length ? `
      <h3 style="color:#1B3A5C;font-size:14px;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Active Litigation</h3>
      <div style="margin-bottom:24px">${litHtml}</div>` : ""}

      ${data.immediate_triggers?.length ? `
      <h3 style="color:#1B3A5C;font-size:14px;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Immediate Triggers</h3>
      <div style="margin-bottom:24px">${triggersHtml}</div>` : ""}

      ${data.strategic_notes ? `
      <h3 style="color:#1B3A5C;font-size:14px;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">Strategic Notes</h3>
      <p style="color:#555;font-size:13px;line-height:1.7">${data.strategic_notes}</p>` : ""}

      <div style="margin-top:24px;text-align:center">
        <a href="https://nazar-ai.com/research" style="background:#1B3A5C;color:white;padding:10px 24px;border-radius:6px;text-decoration:none;font-size:14px">Open Nazar Dashboard</a>
      </div>
      <div style="margin-top:16px;text-align:center;font-size:11px;color:#aaa">
        Generated ${new Date().toLocaleDateString("en-US", {weekday:"long",year:"numeric",month:"long",day:"numeric"})} · nazar-ai.com
      </div>
    </div>
  </div>`;
}

export default router;
