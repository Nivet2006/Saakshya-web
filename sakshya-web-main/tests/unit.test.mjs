import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');

test('shared-contracts mock-events.jsonl has valid v1 lifecycle sequence', () => {
  const jsonlPath = path.join(rootDir, 'shared-contracts', 'mock-events.jsonl');
  assert.ok(fs.existsSync(jsonlPath), 'mock-events.jsonl must exist');
  const lines = fs
    .readFileSync(jsonlPath, 'utf8')
    .trim()
    .split('\n')
    .map((line) => JSON.parse(line));

  assert.equal(lines.length, 46, 'Expected 46 mock v1 events');
  const types = new Set(lines.map((e) => e.type));
  for (const requiredType of [
    'session_ready',
    'partial_transcript',
    'final_transcript',
    'visit_draft_updated',
    'read_back_started',
    'barge_in',
    'tts_cancelled',
    'correction_applied',
    'danger_alert',
    'visit_confirmed',
    'persistence_requested',
    'visit_committed',
  ]) {
    assert.ok(types.has(requiredType), `Missing required v1 event type: ${requiredType}`);
  }

  // Verify field preservation on correction_applied
  const correction = lines.find((e) => e.type === 'correction_applied');
  assert.ok(correction, 'correction_applied event present');
  assert.equal(correction.requires_re_read_back, true);
  assert.ok(correction.corrected_fields.includes('weight_kg'));
  assert.ok(correction.preserved_fields.includes('beneficiary_id'));
  assert.equal(correction.draft.status, 'draft');

  // Verify danger alert stays attached even when subsequent visit events fire
  const committed = lines.find((e) => e.type === 'visit_committed');
  assert.ok(committed, 'visit_committed event present');
  assert.equal(committed.visit.danger_sign_flagged, true);
  assert.ok(committed.visit.persistence_record_id);
});

test('synthetic beneficiaries match Agent 1 BEN-1042..BEN-1048 fixtures in Firestore seed', () => {
  const seedSrc = fs.readFileSync(path.join(rootDir, 'scripts', 'migrate-firebase.mjs'), 'utf8');
  for (const [id, name] of [
    ['BEN-1042', 'Lakshmi Devi'],
    ['BEN-1043', 'Kavitha Rao'],
    ['BEN-1044', 'Baby of Kavitha Rao'],
    ['BEN-1045', 'Sunita Kumari'],
    ['BEN-1046', 'Meena Selvam'],
    ['BEN-1047', 'Anita Devi'],
    ['BEN-1048', 'Lakshmi Narayanan'],
  ]) {
    assert.ok(seedSrc.includes(id), `Missing seeded synthetic ID ${id}`);
    assert.ok(seedSrc.includes(name), `Missing seeded synthetic name ${name}`);
  }

  // Ensure mock-data.ts does not keep hardcoded beneficiaries
  const mockDataSrc = fs.readFileSync(path.join(rootDir, 'src', 'lib', 'mock-data.ts'), 'utf8');
  assert.ok(
    mockDataSrc.includes('export const SYNTHETIC_BENEFICIARIES: Beneficiary[] = [];'),
    'mock-data.ts must be empty array since database stores live records'
  );
});

test('no service-role secrets leaked into src client components', () => {
  const srcFiles = [];
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name.endsWith('.ts') || entry.name.endsWith('.tsx')) srcFiles.push(full);
    }
  };
  walk(path.join(rootDir, 'src'));

  for (const file of srcFiles) {
    const content = fs.readFileSync(file, 'utf8');
    assert.ok(
      !content.includes('SUPABASE_SERVICE_ROLE_KEY'),
      `Service role key must never appear in src/: ${file}`
    );
  }
});

test('supervisor-metrics pure functions exist without hardcoded offset numbers', () => {
  const metricsSrc = fs.readFileSync(
    path.join(rootDir, 'src', 'lib', 'analytics', 'supervisor-metrics.ts'),
    'utf8'
  );
  assert.ok(!metricsSrc.includes('94.2%'), 'Must not contain hardcoded coverage');
  assert.ok(!metricsSrc.includes('visits.length + 12'), 'Must not pad visit count');
});

test('AddPatientModal provides dual mode (typing & speech) with deterministic parser', () => {
  const modalSrc = fs.readFileSync(
    path.join(rootDir, 'src', 'components', 'asha', 'AddPatientModal.tsx'),
    'utf8'
  );
  assert.ok(modalSrc.includes("mode === 'speech'"), 'Must support speech mode');
  assert.ok(modalSrc.includes("mode === 'type'"), 'Must support type mode');
  assert.ok(modalSrc.includes('parseSpokenPatientText'), 'Must implement spoken text parser');
  assert.ok(modalSrc.includes('normalizeIndicDigits'), 'Must support Indic Devanagari numerals');
  assert.ok(modalSrc.includes('SpeechRecognition'), 'Must integrate Web Speech API');
});
