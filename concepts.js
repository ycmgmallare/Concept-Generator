// ===========================================================================
// concepts.js — the 6 pre-authored, EDITABLE prompt templates
// ===========================================================================
//
// This is the file to tweak when you want to change how the moodboards look.
//
// Each concept produces TWO image prompts:
//   • frontPromptTemplate — the HOMEPAGE layout (hero, nav, first impression)
//   • backPromptTemplate  — INNER sections / supporting visuals (features,
//                           product detail, testimonial, footer)
//
// Placeholders get filled in from the user's three inputs at generate time:
//   {idea}      -> the "Idea" field
//   {theme}     -> the "Theme" field
//   {products}  -> the "Products" field
//
// All six share SHARED_FRONT / SHARED_BACK scaffolding so Kie (Nano Banana)
// reliably returns a *website UI design mockup* (Dribbble/Behance style) rather
// than a photo or an abstract image. Edit SHARED_* to change every concept at
// once; edit a concept's own lines to change just that one.
//
// Categories (2 each): Minimalist, Contemporary, Dynamic.
// ===========================================================================

// Wrapper text prepended/appended to every prompt so the model knows we want a
// full web UI screenshot. Tweak here to affect all 6 concepts.
const SHARED_FRONT =
  "High-fidelity full-page website HOMEPAGE UI design mockup, desktop browser screenshot, " +
  "realistic web design shown on a clean canvas. Include a navigation bar, a hero section with " +
  "a headline and a call-to-action button, and a first product/service highlight.";

const SHARED_BACK =
  "High-fidelity website INNER PAGE sections UI design mockup, desktop browser screenshot. " +
  "Show supporting sections stacked vertically: a feature grid, a product/service detail block, " +
  "a testimonial or stats strip, and a footer.";

const SHARED_TAIL =
  "Brand idea: {idea}. Visual theme: {theme}. Showcasing: {products}. " +
  "Polished, intentional, consistent layout, Dribbble / Behance web design showcase, 4k, no watermark.";

// The default desktop aspect ratio passed to Kie for every image. Override per
// concept by adding an `aspectRatio` field to that concept object if desired.
export const DEFAULT_ASPECT_RATIO = "16:9";

export const CONCEPTS = [
  // ----- MINIMALIST ------------------------------------------------------
  {
    number: 1,
    category: "Minimalist",
    conceptName: "Quiet Canvas",
    description:
      "Vast negative space, a restrained near-monochrome palette with a single accent colour, " +
      "and a large refined serif headline. Calm, confident, gallery-like.",
    frontPromptTemplate:
      `${SHARED_FRONT} MINIMALIST aesthetic: generous whitespace, near-monochrome palette with ` +
      `ONE subtle accent colour, large elegant serif headline, thin sparse navigation, a single ` +
      `understated product highlight, plenty of breathing room. ${SHARED_TAIL}`,
    backPromptTemplate:
      `${SHARED_BACK} MINIMALIST aesthetic: airy whitespace, near-monochrome with one accent, ` +
      `elegant serif headings, thin hairline dividers, a calm feature grid and a quiet footer. ` +
      `${SHARED_TAIL}`,
  },
  {
    number: 2,
    category: "Minimalist",
    conceptName: "Editorial Grid",
    description:
      "Swiss / editorial discipline — a strict typographic grid, thin rules, small-caps labels " +
      "and black type on warm off-white. Structured and precise.",
    frontPromptTemplate:
      `${SHARED_FRONT} MINIMALIST Swiss editorial aesthetic: strict typographic grid, thin ruled ` +
      `lines, small-caps section labels, black text on warm off-white, a bold but tidy headline, ` +
      `disciplined alignment, minimal colour. ${SHARED_TAIL}`,
    backPromptTemplate:
      `${SHARED_BACK} MINIMALIST Swiss editorial aesthetic: column grid, thin rules between rows, ` +
      `small-caps labels, black-on-off-white, structured feature and detail blocks, a precise ` +
      `gridded footer. ${SHARED_TAIL}`,
  },

  // ----- CONTEMPORARY ----------------------------------------------------
  {
    number: 3,
    category: "Contemporary",
    conceptName: "Soft Bento",
    description:
      "A modern bento-box grid of rounded cards over a soft gradient mesh, pastel tones and " +
      "friendly sans-serif type. Expressive yet professional SaaS polish.",
    frontPromptTemplate:
      `${SHARED_FRONT} CONTEMPORARY aesthetic: modern bento-box grid of rounded-corner cards, ` +
      `soft pastel gradient-mesh background, friendly geometric sans-serif, gentle shadows, a ` +
      `clean hero card with CTA, modern SaaS feel. ${SHARED_TAIL}`,
    backPromptTemplate:
      `${SHARED_BACK} CONTEMPORARY aesthetic: bento-style rounded cards in a varied grid, soft ` +
      `pastel gradient accents, friendly sans-serif, feature cards with icons, a stats strip, a ` +
      `rounded footer. ${SHARED_TAIL}`,
  },
  {
    number: 4,
    category: "Contemporary",
    conceptName: "Gradient Aurora",
    description:
      "A tasteful aurora gradient hero with floating glassmorphism cards and crisp modern type. " +
      "Premium startup polish — vivid but controlled.",
    frontPromptTemplate:
      `${SHARED_FRONT} CONTEMPORARY aesthetic: vivid yet tasteful aurora gradient hero, floating ` +
      `frosted-glass (glassmorphism) UI cards, crisp modern sans-serif, subtle glow and depth, ` +
      `premium startup landing-page polish. ${SHARED_TAIL}`,
    backPromptTemplate:
      `${SHARED_BACK} CONTEMPORARY aesthetic: soft aurora gradient accents on a light background, ` +
      `glassmorphism feature cards, crisp modern type, a sleek pricing or detail block, a refined ` +
      `footer with glow accents. ${SHARED_TAIL}`,
  },

  // ----- DYNAMIC ---------------------------------------------------------
  {
    number: 5,
    category: "Dynamic",
    conceptName: "Kinetic Bold",
    description:
      "Oversized display sans-serif, an asymmetric layout and a black canvas with one electric " +
      "accent. High energy, motion-implied, attention-grabbing.",
    frontPromptTemplate:
      `${SHARED_FRONT} DYNAMIC aesthetic: oversized bold display sans-serif headline, high-contrast ` +
      `near-black background with ONE electric accent colour, bold asymmetric layout, strong diagonal ` +
      `energy, a punchy CTA. Visually striking, motion-implied. ${SHARED_TAIL}`,
    backPromptTemplate:
      `${SHARED_BACK} DYNAMIC aesthetic: dark high-contrast background with one electric accent, ` +
      `oversized bold type, asymmetric feature blocks, large numerals for stats, a bold footer. ` +
      `Energetic and striking. ${SHARED_TAIL}`,
  },
  {
    number: 6,
    category: "Dynamic",
    conceptName: "Brutalist Impact",
    description:
      "Raw brutalist web design — stark black-and-white contrast, heavy visible grid borders, " +
      "huge type and monospace accents. Unapologetic and memorable.",
    frontPromptTemplate:
      `${SHARED_FRONT} DYNAMIC brutalist aesthetic: raw stark black-and-white high contrast, heavy ` +
      `visible grid borders and boxes, enormous bold type, monospace label accents, blunt CTA button, ` +
      `unpolished-on-purpose web brutalism. ${SHARED_TAIL}`,
    backPromptTemplate:
      `${SHARED_BACK} DYNAMIC brutalist aesthetic: stark black-and-white, thick boxed borders around ` +
      `each section, oversized type, monospace captions, a raw bordered feature grid and a blocky ` +
      `footer. ${SHARED_TAIL}`,
  },
];

// Fill {idea}/{theme}/{products} placeholders in a single template string.
function fill(template, inputs) {
  return template
    .replaceAll("{idea}", inputs.idea)
    .replaceAll("{theme}", inputs.theme)
    .replaceAll("{products}", inputs.products);
}

// Turn the templates above into the 6 finished concept objects the server
// returns to the browser. Each gets resolved frontPrompt/backPrompt strings.
export function buildConcepts(inputs) {
  return CONCEPTS.map((c) => ({
    number: c.number,
    category: c.category,
    conceptName: c.conceptName,
    description: c.description,
    aspectRatio: c.aspectRatio ?? DEFAULT_ASPECT_RATIO,
    frontPrompt: fill(c.frontPromptTemplate, inputs),
    backPrompt: fill(c.backPromptTemplate, inputs),
  }));
}
