// generated_from: behaviors/convert
// spec_hash: 6b05e494d1223d781aee2c84aa5807928235827ce7a5f9ad5a6be1e9d0712d20
// generated_at: 2026-03-10T09:02:40.992161+00:00
// agent: implementation-agent
const { readAndValidate } = require('../utils/file_system');
const { parseCSV } = require('./parser');
const { writeJSON } = require('./writer');

async function convert(input, output, options) {
  const fileData = await readAndValidate(input);
  const { headers, rows, count } = parseCSV(fileData, options.detectTypes);
  await writeJSON(output, rows, options);
  process.stderr.write(`Converted ${count} rows from ${input} to ${output || 'stdout'}\n`);
}

module.exports = { convert };