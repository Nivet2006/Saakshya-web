/**
 * Rule-Based Clinical Risk Engine (JavaScript Module)
 * Compatible with pure Node, Jest, and Webpack/Next.js imports.
 */

import {
  calculateRisk as tsCalculateRisk,
  assessClinicalRisk as tsAssessClinicalRisk,
  normalizePatientCategory,
  extractRiskFactors,
  getRiskColorClasses,
} from './riskEngine.ts';

export const calculateRisk = tsCalculateRisk;
export const assessClinicalRisk = tsAssessClinicalRisk;
export { normalizePatientCategory, extractRiskFactors, getRiskColorClasses };
export default calculateRisk;
