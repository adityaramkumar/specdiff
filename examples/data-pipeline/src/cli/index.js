// generated_from: behaviors/load
// spec_hash: 15f4801046c0711f2faaa6cc531935b309899032e5bcc3234d072017a1169ea0
// generated_at: 2026-03-10T09:07:19.973302+00:00
// agent: implementation-agent
const { program } = require('commander');
const { load } = require('../domain/loader');

program
  .command('load <transform_dir>')
  .requiredOption('--output <output_dir>')
  .action(async (transform_dir, options) => {
    try {
      await load(transform_dir, options.output);
    } catch (err) {
      process.stderr.write(`Error: ${err.message}\n`);
      process.exit(1);
    }
  });

program.parse();