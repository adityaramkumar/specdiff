// generated_from: behaviors/load
// spec_hash: 15f4801046c0711f2faaa6cc531935b309899032e5bcc3234d072017a1169ea0
// generated_at: 2026-03-10T09:07:19.973302+00:00
// agent: implementation-agent
const fs = require('fs');
const path = require('path');
const { readEvents } = require('../infrastructure/file_reader');
const { partitionEvents } = require('./partitioner');
const { writePartitions } = require('../infrastructure/file_writer');
const { sortEvents } = require('../utils/sorter');

async function load(transformDir, outputDir) {
  if (!fs.existsSync(transformDir)) {
    throw new Error(`directory not found: ${transformDir}`);
  }

  const events = await readEvents(transformDir);
  if (events.length === 0) {
    throw new Error(`no events found in ${transformDir}`);
  }

  const sorted = sortEvents(events);
  const partitions = partitionEvents(sorted);
  
  await writePartitions(outputDir, partitions);
  
  console.log(`Loaded ${events.length} events into ${Object.keys(partitions).length} partitions`);
}