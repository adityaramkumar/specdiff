// generated_from: behaviors/convert
// spec_hash: 6b05e494d1223d781aee2c84aa5807928235827ce7a5f9ad5a6be1e9d0712d20
// generated_at: 2026-03-10T09:02:40.992161+00:00
// agent: implementation-agent
function handleError(err) {
  const [code, meta] = err.message.split(':');
  const messages = {
    'FILE_NOT_FOUND': `Error: file not found: ${meta}`,
    'EMPTY_FILE': `Error: empty file: ${meta}`,
    'MALFORMED_CSV': `Error: malformed CSV at line ${meta}: unclosed quote`,
    'DUPLICATE_COLUMN': `Error: duplicate column name: ${meta}`,
    'FILE_TOO_LARGE': `Error: file too large: ${meta} bytes (max 100 MB)`
  };
  process.stderr.write(messages[code] || `Error: ${err.message}`);
}
module.exports = { handleError };