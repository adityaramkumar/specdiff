// generated_from: behaviors/transform
// spec_hash: 0c693b22255ee8ba03d47bf5d7d244de4eb44cb5bf9c27d0585f3b66550a2eca
// generated_at: 2026-03-10T09:07:27.851408+00:00
// agent: implementation-agent
const { v5: uuidv5 } = require('uuid');
const NAMESPACE = '6ba7b810-9dad-11d1-80b4-00c04fd430c8';

function sessionize(events) {
  const userGroups = {};
  events.forEach(e => {
    if (!userGroups[e.user_id]) userGroups[e.user_id] = [];
    userGroups[e.user_id].push(e);
  });

  const processed = [];
  let sessionCount = 0;

  for (const userId in userGroups) {
    let currentSessionStart = null;
    let currentSessionId = null;
    let seq = 0;

    userGroups[userId].forEach(event => {
      const time = new Date(event.timestamp_utc).getTime();
      const gap = currentSessionStart ? (time - currentSessionStart) : Infinity;

      if (userId === 'anonymous' || gap > 30 * 60 * 1000) {
        currentSessionStart = time;
        currentSessionId = uuidv5(`${userId}:${event.timestamp_utc}`, NAMESPACE);
        sessionCount++;
        seq = 1;
      } else {
        seq++;
      }

      processed.push({
        ...event,
        enrichments: { session_id: currentSessionId, event_sequence: seq }
      });
    });
  }

  processed.sort((a, b) => new Date(a.timestamp_utc) - new Date(b.timestamp_utc));
  return { processed, sessionCount };
}

module.exports = { sessionize };