// generated_from: behaviors/ingest
// spec_hash: 6a1f8cd3e485a592344368a12c604354baaef65476af925fc3a312a4d53a93f5
// generated_at: 2026-03-10T09:07:11.661803+00:00
// agent: implementation-agent
const { validateUUID, validateISO8601, allowedTypes, allowedSources } = require('../types/event');

function validateEvent(event) {
  if (!validateUUID(event.event_id)) return 'invalid event_id';
  if (!allowedTypes.includes(event.event_type)) return 'invalid event_type';
  if (!validateISO8601(event.timestamp)) return 'invalid timestamp';
  if (event.user_id !== null && !validateUUID(event.user_id)) return 'invalid user_id';
  if (typeof event.properties !== 'object' || event.properties === null || Array.isArray(event.properties)) return 'invalid properties';
  if (!allowedSources.includes(event.source)) return 'invalid source';
  return null;
}
module.exports = { validateEvent };