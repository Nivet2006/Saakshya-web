/**
 * Devanagari & Indic Digit Normalization Utilities
 *
 * Grounded in AASHA's offline-first architecture.
 * Ensures numerals in Indian scripts (Devanagari, Kannada, Tamil, Telugu, Bengali, Gujarati, Malayalam)
 * like "२.५ किलो", "५३", or "१०२" are reliably converted to standard ASCII digits ("2.5 किलो", "53", "102")
 * for robust numerical extraction, clinical thresholds, and visit field mapping.
 */

export const DEVANAGARI_DIGIT_MAP: Record<string, string> = {
  '०': '0',
  '१': '1',
  '२': '2',
  '३': '3',
  '४': '4',
  '५': '5',
  '६': '6',
  '७': '7',
  '८': '8',
  '९': '9',
};

export const ALL_INDIC_DIGIT_MAP: Record<string, string> = {
  // Devanagari (Hindi, Marathi, Nepali, Sanskrit)
  '०': '0',
  '१': '1',
  '२': '2',
  '३': '3',
  '४': '4',
  '५': '5',
  '६': '6',
  '७': '7',
  '८': '8',
  '९': '9',

  // Kannada
  '೦': '0',
  '೧': '1',
  '೨': '2',
  '೩': '3',
  '೪': '4',
  '೫': '5',
  '೬': '6',
  '೭': '7',
  '೮': '8',
  '೯': '9',

  // Tamil
  '௦': '0',
  '௧': '1',
  '௨': '2',
  '௩': '3',
  '௪': '4',
  '௫': '5',
  '௬': '6',
  '௭': '7',
  '௮': '8',
  '௯': '9',

  // Telugu
  '౦': '0',
  '౧': '1',
  '౨': '2',
  '౩': '3',
  '౪': '4',
  '౫': '5',
  '౬': '6',
  '౭': '7',
  '౮': '8',
  '౯': '9',

  // Bengali / Assamese
  '০': '0',
  '১': '1',
  '২': '2',
  '৩': '3',
  '৪': '4',
  '৫': '5',
  '৬': '6',
  '৭': '7',
  '৮': '8',
  '৯': '9',

  // Gujarati
  '૦': '0',
  '૧': '1',
  '૨': '2',
  '૩': '3',
  '૪': '4',
  '૫': '5',
  '૬': '6',
  '૭': '7',
  '૮': '8',
  '૯': '9',

  // Malayalam
  '൦': '0',
  '൧': '1',
  '൨': '2',
  '൩': '3',
  '൪': '4',
  '൫': '5',
  '൬': '6',
  '൭': '7',
  '൮': '8',
  '൯': '9',
};

const INDIC_DIGIT_REGEX = /[०-९೦-೯௦-௯౦-౯০-৯૦-૯൦-൯]/g;
const DEVANAGARI_ONLY_REGEX = /[०-९]/g;

/**
 * Normalizes Devanagari numerals (०-९) to ASCII digits (0-9).
 * Preserves all surrounding text and punctuation.
 *
 * Example:
 * normalizeDevanagariDigits("वजन २.५ किलो") -> "वजन 2.5 किलो"
 */
export function normalizeDevanagariDigits(input?: string | null): string {
  if (!input || typeof input !== 'string') return '';
  return input.replace(DEVANAGARI_ONLY_REGEX, (d) => DEVANAGARI_DIGIT_MAP[d] || d);
}

/**
 * Normalizes all major Indic script numerals (Devanagari, Kannada, Tamil, Telugu,
 * Bengali, Gujarati, Malayalam) to ASCII digits (0-9).
 * Also collapses spaced ASR decimals like "2 . 5" to "2.5".
 */
export function normalizeDigits(input?: string | null): string {
  if (!input || typeof input !== 'string') return '';
  let out = input.replace(INDIC_DIGIT_REGEX, (d) => ALL_INDIC_DIGIT_MAP[d] || d);
  // Collapse ASR spaced decimals like "2 . 5" or "२ . ५" into "2.5"
  out = out.replace(/(\d)\s*\.\s*(\d)/g, '$1.$2');
  return out;
}

/**
 * Extracts a normalized floating-point weight in kg from Devanagari or mixed Indic text.
 * Handles "२.५ किलो", "२ किलो ५०० ग्राम", "२५०० ग्राम", "2.8 kg", etc.
 */
export function extractWeightFromIndicText(text?: string | null): {
  weightKg: number | null;
  rawMatched: string | null;
} {
  if (!text) return { weightKg: null, rawMatched: null };

  const normalized = normalizeDigits(text);

  // Pattern 1: Compound "2 किलो 500 ग्राम" or "2 kg 500 g"
  const compoundMatch = normalized.match(
    /(\d+(?:\.\d+)?)\s*(?:किलो|kg|kilo)\s*(?:और|and)?\s*(\d+(?:\.\d+)?)\s*(?:ग्राम|gram|gm|g)\b/i
  );
  if (compoundMatch) {
    const kg = parseFloat(compoundMatch[1]) || 0;
    const g = parseFloat(compoundMatch[2]) || 0;
    const total = parseFloat((kg + g / 1000).toFixed(3));
    return { weightKg: total, rawMatched: compoundMatch[0] };
  }

  // Pattern 2: Grams alone "2500 ग्राम" or "2500 g"
  const gramMatch = normalized.match(/(\d+(?:\.\d+)?)\s*(?:ग्राम|gram|gm|g)\b/i);
  if (gramMatch) {
    const val = parseFloat(gramMatch[1]);
    if (val >= 400 && val <= 10000) {
      return { weightKg: parseFloat((val / 1000).toFixed(3)), rawMatched: gramMatch[0] };
    }
  }

  // Pattern 3: Standard decimal or integer kg: "2.5 किलो", "3 किलो", "2.8 kg"
  const kgMatch = normalized.match(/(\d+(?:\.\d+)?)\s*(?:किलो|kg|kilo|kgs)\b/i);
  if (kgMatch) {
    const val = parseFloat(kgMatch[1]);
    if (val >= 0.4 && val <= 200) {
      return { weightKg: parseFloat(val.toFixed(2)), rawMatched: kgMatch[0] };
    }
  }

  // Pattern 4: Cue-preceded number: "वजन 2.5", "weight 3.1"
  const cueMatch = normalized.match(/(?:वजन|weight|weight is|वजन है)\s*:?\s*(\d+(?:\.\d+)?)/i);
  if (cueMatch) {
    const val = parseFloat(cueMatch[1]);
    if (val >= 0.4 && val <= 200) {
      return { weightKg: parseFloat(val.toFixed(2)), rawMatched: cueMatch[0] };
    }
  }

  return { weightKg: null, rawMatched: null };
}

export default normalizeDigits;
