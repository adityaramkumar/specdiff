// generated_from: contracts/schemas/raw-events
// spec_hash: 6eced18bceb8e4b00bcc2656f2b50decf0cd0afdd960b5bf4d162a70a2e71825
// generated_at: 2026-03-10T09:06:52.941389+00:00
// agent: implementation-agent
import * as readline from 'readline';
import { validateEvent } from '../validation/event_validator';
import { writeToDeadLetter } from '../storage/dead_letter_writer';

export async function processStream(inputStream: NodeJS.ReadableStream): Promise<void> {
  const rl = readline.createInterface({ input: inputStream });
  for await (const line of rl) {
    if (line.length > 65536) {
      writeToDeadLetter({ error: 'Line exceeds 64KB limit', raw: line });
      continue;
    }
    try {
      const event = JSON.parse(line);
      const { valid, error } = validateEvent(event);
      if (!valid) {
        writeToDeadLetter({ error, event });
      }
    } catch (e) {
      writeToDeadLetter({ error: 'Invalid JSON', raw: line });
    }
  }
}