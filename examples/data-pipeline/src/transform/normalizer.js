// generated_from: behaviors/transform
// spec_hash: 0c693b22255ee8ba03d47bf5d7d244de4eb44cb5bf9c27d0585f3b66550a2eca
// generated_at: 2026-03-10T09:07:27.851408+00:00
// agent: implementation-agent
function normalize(event) {
  const dateObj = new Date(event.timestamp);
  const timestamp_utc = dateObj.toISOString().split('.')[0] + 'Z';
  const is_anonymous = event.user_id === null;
  
  return {
    event_id: event.event_id,
    event_type: event.event_type,
    timestamp_utc,
    date: dateObj.toISOString().split('T')[0],
    hour: dateObj.getUTCHours(),
    user_id: is_anonymous ? 'anonymous' : event.user_id,
    is_anonymous,
    source: event.source,
    properties: event.properties
  };
}

module.exports = { normalize };