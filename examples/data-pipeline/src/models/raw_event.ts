// generated_from: contracts/schemas/raw-events
// spec_hash: 6eced18bceb8e4b00bcc2656f2b50decf0cd0afdd960b5bf4d162a70a2e71825
// generated_at: 2026-03-10T09:06:52.941389+00:00
// agent: implementation-agent
export type EventType = 'page_view' | 'click' | 'purchase' | 'signup';
export type SourceType = 'web' | 'mobile' | 'api';

export interface RawEvent {
  event_id: string;
  event_type: EventType;
  timestamp: string;
  user_id: string | null;
  properties: Record<string, any>;
  source: SourceType;
}