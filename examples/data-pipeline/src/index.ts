// generated_from: contracts/schemas/raw-events
// spec_hash: 6eced18bceb8e4b00bcc2656f2b50decf0cd0afdd960b5bf4d162a70a2e71825
// generated_at: 2026-03-10T09:06:52.941389+00:00
// agent: implementation-agent
import { processStream } from './processing/stream_processor';
import * as fs from 'fs';

const inputStream = fs.createReadStream(process.argv[2]);
processStream(inputStream).catch(console.error);