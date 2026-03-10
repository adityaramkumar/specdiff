// generated_from: contracts/schemas/raw-events
// spec_hash: 6eced18bceb8e4b00bcc2656f2b50decf0cd0afdd960b5bf4d162a70a2e71825
// generated_at: 2026-03-10T09:06:52.941389+00:00
// agent: implementation-agent
import { RawEvent } from '../models/raw_event';
import { isValidUUID } from '../utils/uuid_validator';

export function validateEvent(event: any): { valid: boolean; error?: string } {
  if (!event || typeof event !== 'object' || Array.isArray(event)) return { valid: false, error: 'Invalid event format' };
  if (!isValidUUID(event.event_id)) return { valid: false, error: 'Invalid event_id' };
  if (!['page_view', 'click', 'purchase', 'signup'].includes(event.event_type)) return { valid: false, error: 'Invalid event_type' };
  if (isNaN(Date.parse(event.timestamp))) return { valid: false, error: 'Invalid timestamp' };
  if (event.user_id !== null && event.user_id !== undefined && !isValidUUID(event.user_id)) return { valid: false, error: 'Invalid user_id' };
  if (!event.properties || typeof event.properties !== 'object' || Array.isArray(event.properties)) return { valid: false, error: 'Invalid properties' };
  if (!['web', 'mobile', 'api'].includes(event.source)) return { valid: false, error: 'Invalid source' };
  return { valid: true };
}