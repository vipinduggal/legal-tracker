import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")
verifier_path = os.path.join(base, "src", "contactVerifier.js")

with open(verifier_path, 'r') as f:
    content = f.read()

# The problem: one big Perplexity query returns thin results
# Fix: run 3 focused searches and combine them

old_perplexity_query = '''  // Step 1: Perplexity live search for current intelligence
  const perplexityQuery = `Today is ${todayStr}. Search for the most recent news and events about ${account.name} (${account.industry}) from ${sixMonthsAgoStr} to today only.

Find:
1. Any new lawsuits, regulatory investigations, or government actions filed or announced since ${threeMonthsAgoStr}
2. Recent earnings calls or financial results from the last 2 quarters — what did leadership say about costs, legal spend, or headcount?
3. Any restructuring, layoffs, cost reduction programs, or efficiency initiatives announced since ${sixMonthsAgoStr}
4. Any M&A activity (acquisitions, mergers, divestitures) announced since ${sixMonthsAgoStr}
5. Any senior legal leadership changes (CLO, GC, Head of Legal Ops) since ${sixMonthsAgoStr}
6. Any major contract wins, new markets, or business expansions since ${sixMonthsAgoStr} that would increase legal workload

Be specific: include dates, dollar amounts, and names. Only report events from ${sixMonthsAgoStr} to today. If you find nothing current for a category, say so explicitly.`;

  let perplexityAnswer = "";
  let citations = [];

  try {
    const response = await axios.post(
      "https://api.perplexity.ai/chat/completions",
      {
        model: "sonar",
        messages: [
          {
            role: "system",
            content: `You are a legal intelligence researcher. Today is ${todayStr}. Only report information from ${sixMonthsAgoStr} or ${threeMonthsAgoStr} or more recently. Be specific with dates. Do not reference anything older than ${sixMonthsAgoStr}.`,
          },
          { role: "user", content: perplexityQuery },
        ],
        max_tokens: 1500,
      },
      {
        headers: {
          Authorization: "Bearer " + PERPLEXITY_KEY,
          "Content-Type": "application/json",
        },
        timeout: 25000,
      }
    );

    perplexityAnswer = response.data?.choices?.[0]?.message?.content || "";
    citations = response.data?.citations || [];

    if (!perplexityAnswer || perplexityAnswer.length < 50) {
      logger.warn("Perplexity returned empty response for " + account.name);
      return null;
    }

    logger.info("Perplexity live search complete for " + account.name + " (" + perplexityAnswer.length + " chars)");

  } catch (err) {
    logger.warn("Perplexity live search failed for " + account.name, { error: err.message });
    return null;
  }'''

new_perplexity_query = '''  // Step 1: Run 3 focused Perplexity searches and combine results
  // Breaking into focused queries gets much better results than one broad query

  const searches = [
    {
      label: "litigation",
      query: `What lawsuits, legal disputes, patent infringement cases, class actions, or regulatory investigations involve ${account.name} in ${sixMonthsAgoStr} to ${todayStr}? Include case names, filing dates, courts, and dollar amounts where known. Focus on NEW cases filed in the last 6 months.`,
    },
    {
      label: "financial",
      query: `What did ${account.name} report in their most recent earnings call or quarterly results in 2026? Focus on: legal costs, litigation reserves, loss contingencies, restructuring charges, cost reduction programs, M&A deals, and any comments about legal department spending or headcount. Include specific dollar amounts and dates.`,
    },
    {
      label: "business",
      query: `What major business changes has ${account.name} announced in the last 6 months (${sixMonthsAgoStr} to ${todayStr})? Focus on: acquisitions, mergers, divestitures, major new contracts, expansion into new markets, regulatory approvals or rejections, export controls, government investigations, or leadership changes in legal/compliance roles.`,
    },
  ];

  let perplexityAnswer = "";
  let citations = [];

  for (const search of searches) {
    try {
      const response = await axios.post(
        "https://api.perplexity.ai/chat/completions",
        {
          model: "sonar",
          messages: [
            {
              role: "system",
              content: `You are a legal and business intelligence researcher. Today is ${todayStr}. Provide specific, factual information with dates. Only include information from ${sixMonthsAgoStr} to today. If you find nothing relevant, say "No recent information found for this category."`,
            },
            { role: "user", content: search.query },
          ],
          max_tokens: 800,
        },
        {
          headers: {
            Authorization: "Bearer " + PERPLEXITY_KEY,
            "Content-Type": "application/json",
          },
          timeout: 20000,
        }
      );

      const answer = response.data?.choices?.[0]?.message?.content || "";
      const srcs = response.data?.citations || [];

      if (answer && answer.length > 30 && !answer.toLowerCase().includes("no recent information found")) {
        perplexityAnswer += `\n\n=== ${search.label.toUpperCase()} INTELLIGENCE ===\n${answer}`;
        citations = [...citations, ...srcs];
        logger.info(`Perplexity ${search.label} search complete for ${account.name} (${answer.length} chars)`);
      } else {
        logger.info(`Perplexity ${search.label} search found nothing current for ${account.name}`);
      }

      await new Promise(r => setTimeout(r, 500));

    } catch (err) {
      logger.warn(`Perplexity ${search.label} search failed for ${account.name}: ${err.message}`);
    }
  }

  if (!perplexityAnswer || perplexityAnswer.trim().length < 100) {
    logger.warn(`Perplexity found no current intelligence for ${account.name}`);
    return null;
  }

  // Deduplicate citations
  citations = [...new Map(citations.map(c => [c, c])).values()].slice(0, 5);
  logger.info(`Combined Perplexity intelligence for ${account.name}: ${perplexityAnswer.length} chars`);'''

if old_perplexity_query in content:
    content = content.replace(old_perplexity_query, new_perplexity_query)
    print("Done — Perplexity queries split into 3 focused searches")
else:
    print("WARNING — query pattern not found exactly, searching...")
    idx = content.find("Step 1: Perplexity live search")
    if idx > 0:
        print("Found at index " + str(idx))
        print("May need manual update")
    else:
        print("Not found — check contactVerifier.js manually")

with open(verifier_path, 'w') as f:
    f.write(content)

print("")
print("Test:")
print('  npm run research:account "AMD"')
print("")
print("Watch for 3 Perplexity search lines in the output:")
print("  [info] Perplexity litigation search complete for AMD")
print("  [info] Perplexity financial search complete for AMD")
print("  [info] Perplexity business search complete for AMD")
