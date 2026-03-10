// generated_from: behaviors/load
// spec_hash: 15f4801046c0711f2faaa6cc531935b309899032e5bcc3234d072017a1169ea0
// generated_at: 2026-03-10T09:07:19.973302+00:00
// agent: implementation-agent
function sortEvents(events) {
  return [...events].sort((a, b) => 
    new Date(a.timestamp_utc) - new Date(b.timestamp_utc)
  );
}

module.exports = { sortEvents };