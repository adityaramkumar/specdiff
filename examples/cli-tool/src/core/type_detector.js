// generated_from: behaviors/convert
// spec_hash: 6b05e494d1223d781aee2c84aa5807928235827ce7a5f9ad5a6be1e9d0712d20
// generated_at: 2026-03-10T09:02:40.992161+00:00
// agent: implementation-agent
function inferType(val) {
  if (val === '') return null;
  if (/^-?\d+$/.test(val)) return parseInt(val, 10);
  if (/^-?\d+\.\d+$/.test(val)) return parseFloat(val);
  if (val.toLowerCase() === 'true') return true;
  if (val.toLowerCase() === 'false') return false;
  return val;
}
module.exports = { inferType };