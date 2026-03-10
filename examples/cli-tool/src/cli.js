// generated_from: behaviors/convert
// spec_hash: 6b05e494d1223d781aee2c84aa5807928235827ce7a5f9ad5a6be1e9d0712d20
// generated_at: 2026-03-10T09:02:40.992161+00:00
// agent: implementation-agent
const { convert } = require('./core/converter');
const { handleError } = require('./errors/error_handler');

const args = process.argv.slice(2);
const input = args.filter(a => !a.startsWith('-'))[0];
const output = args.filter(a => !a.startsWith('-'))[1] || null;
const detectTypes = args.includes('--detect-types');
const compact = args.includes('--compact');

if (!input) process.exit(1);

convert(input, output, { detectTypes, compact }).catch(err => {
  handleError(err);
  process.exit(1);
});