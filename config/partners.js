// partners.js — Tracked litigation partners (sales targets).
// v1 validation set: 10 partners, Seattle + San Francisco AmLaw 200 offices,
// biased toward federal / defense-side / discovery-heavy work (your buyers).
//
// IMPORTANT: these are CANDIDATES, not pre-verified. Public bios confirm each is
// a current litigation partner; they do NOT confirm a live federal defense case.
// The tool's job is to find that. A "no cases" result may be a coverage gap OR
// a partner whose current work is state-side / quiet — read results with that lens.
//
// Fields:
//   id, name, nameVariants, firm, city, tier, knownCase (optional), active

export const PARTNERS = [
  // ---------- SEATTLE ----------
  {
    id: "burnside-fred-dwt",
    name: "Fred B. Burnside",
    nameVariants: ["Burnside", "Fred Burnside", "Frederick Burnside"],
    firm: "Davis Wright Tremaine",
    city: "Seattle",
    tier: "partner",
    active: true,
  },
  {
    id: "maguire-robert-dwt",
    name: "Robert J. Maguire",
    nameVariants: ["Maguire", "Robert Maguire", "Rob Maguire"],
    firm: "Davis Wright Tremaine",
    city: "Seattle",
    tier: "partner",
    active: true,
  },
  {
    id: "rummage-stephen-dwt",
    name: "Stephen M. Rummage",
    nameVariants: ["Rummage", "Stephen Rummage", "Steve Rummage"],
    firm: "Davis Wright Tremaine",
    city: "Seattle",
    tier: "partner",
    active: true,
  },
  {
    id: "kramer-kevin-dwt",
    name: "Kevin Kramer",
    nameVariants: ["Kramer", "Kevin Kramer"],
    firm: "Davis Wright Tremaine",
    city: "Seattle",
    tier: "partner",
    // Joined DWT Seattle May 2026 from Amazon — FRESHNESS test case.
    active: true,
  },
  {
    id: "parris-mark-orrick",
    name: "Mark S. Parris",
    nameVariants: ["Parris", "Mark Parris"],
    firm: "Orrick",
    city: "Seattle",
    tier: "partner",
    active: true,
  },
  {
    id: "swaminathan-aravind-orrick",
    name: "Aravind Swaminathan",
    nameVariants: ["Swaminathan", "Aravind Swaminathan"],
    firm: "Orrick",
    city: "Seattle",
    tier: "partner",
    active: true,
  },

  // ---------- SAN FRANCISCO ----------
  {
    id: "rocca-brian-morganlewis",
    name: "Brian C. Rocca",
    nameVariants: ["Rocca", "Brian Rocca"],
    firm: "Morgan Lewis",
    city: "San Francisco",
    tier: "partner",
    active: true,
  },
  {
    id: "li-luis-wsgr",
    name: "Luis Li",
    nameVariants: ["Luis Li"],
    firm: "Wilson Sonsini",
    city: "San Francisco",
    tier: "partner",
    // Common short name — disambiguation stress test. Watch for false matches.
    active: true,
  },
  {
    id: "anscombe-anthony-steptoe",
    name: "Anthony J. Anscombe",
    nameVariants: ["Anscombe", "Anthony Anscombe"],
    firm: "Steptoe",
    city: "San Francisco",
    tier: "partner",
    active: true,
  },
  {
    id: "tangri-ragesh-mofo",
    name: "Ragesh K. Tangri",
    nameVariants: ["Tangri", "Ragesh Tangri"],
    firm: "Morrison & Foerster",
    city: "San Francisco",
    tier: "partner",
    knownCase: { caption: "Reddit, Inc. v. Anthropic, PBC", defendant: "Anthropic" },
    // KNOWN-GOOD CONTROL — validated clean earlier.
    active: true,
  },
];
