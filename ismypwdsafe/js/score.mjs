import { webcrypto } from 'node:crypto';
import { ZxcvbnFactory } from '@zxcvbn-ts/core';
import * as common from '@zxcvbn-ts/language-common';
import * as en from '@zxcvbn-ts/language-en';
import { matcherPwnedFactory } from '@zxcvbn-ts/matcher-pwned';

// Node 18 exposes Web Crypto as require('node:crypto').webcrypto, not as a
// global. The official HIBP matcher uses globalThis.crypto.subtle.
if (!globalThis.crypto) {
  Object.defineProperty(globalThis, 'crypto', {
    value: webcrypto,
    configurable: true,
  });
}

const ENGINE_VERSION = '4.2.0';
const HIBP_URL = 'https://api.pwnedpasswords.com/range/';

const options = {
  dictionary: { ...common.dictionary, ...en.dictionary },
  graphs: common.adjacencyGraphs,
  translations: en.translations,
};

const withoutHibp = new ZxcvbnFactory(options);

const pwnedMatcher = matcherPwnedFactory(globalThis.fetch, {
  url: HIBP_URL,
  // The zxcvbn-ts default silently ignores network errors. imps must never
  // report a password as safe when the breach check could not run.
  networkErrorHandler: (error) => {
    throw error instanceof Error ? error : new Error(String(error));
  },
});

const withHibp = new ZxcvbnFactory(options, { pwned: pwnedMatcher });

const MATCH_KEYS = {
  matchedWord: 'matched_word',
  dictionaryName: 'dictionary_name',
  baseToken: 'base_token',
  baseGuesses: 'base_guesses',
  repeatCount: 'repeat_count',
  sequenceName: 'sequence_name',
  sequenceSpace: 'sequence_space',
  regexName: 'regex_name',
  regexMatch: 'regex_match',
  shiftedCount: 'shifted_count',
  pwnedAmount: 'pwned_amount',
  subDisplay: 'sub_display',
  guessesLog10: 'guesses_log10',
  uppercaseVariations: 'uppercase_variations',
  l33tVariations: 'l33t_variations',
};

const CRACK_TIMES = [
  ['onlineThrottlingXPerHour', 'online_throttling_100_per_hour'],
  ['onlineNoThrottlingXPerSecond', 'online_no_throttling_10_per_second'],
  ['offlineSlowHashingXPerSecond', 'offline_slow_hashing_1e4_per_second'],
  ['offlineFastHashingXPerSecond', 'offline_fast_hashing_1e10_per_second'],
];

function normalizeMatch(match) {
  const out = {};
  for (const [key, value] of Object.entries(match)) {
    out[MATCH_KEYS[key] || key] = value;
  }
  return out;
}

function normalizeResult(result, { pwned, pwnedCount, hibpStatus, hibpError = null }) {
  const seconds = {};
  const display = {};
  for (const [source, target] of CRACK_TIMES) {
    const value = result.crackTimes?.[source];
    seconds[target] = value?.seconds ?? null;
    display[target] = value?.display ?? 'unknown';
  }

  return {
    engine: 'ts',
    engine_version: ENGINE_VERSION,
    score: result.score,
    guesses: result.guesses,
    guesses_log10: result.guessesLog10,
    crack_times_seconds: seconds,
    crack_times_display: display,
    feedback: {
      warning: result.feedback?.warning ?? null,
      suggestions: result.feedback?.suggestions ?? [],
    },
    sequence: result.sequence.map(normalizeMatch),
    calc_time: result.calcTime,
    pwned,
    pwned_count: pwnedCount,
    hibp_status: hibpStatus,
    hibp_error: hibpError,
  };
}

function readStdin() {
  return new Promise((resolve, reject) => {
    const chunks = [];
    process.stdin.on('data', (chunk) => chunks.push(chunk));
    process.stdin.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    process.stdin.on('error', reject);
  });
}

async function main() {
  const input = JSON.parse(await readStdin());
  const password = input.password;
  const checkBreach = input.check_breach === true;

  if (!checkBreach) {
    const result = withoutHibp.check(password);
    process.stdout.write(JSON.stringify(normalizeResult(result, {
      pwned: null,
      pwnedCount: null,
      hibpStatus: 'disabled',
    })));
    return;
  }

  if (typeof globalThis.fetch !== 'function') {
    const result = withoutHibp.check(password);
    process.stdout.write(JSON.stringify(normalizeResult(result, {
      pwned: null,
      pwnedCount: null,
      hibpStatus: 'error',
      hibpError: 'global fetch is unavailable in this Node.js runtime',
    })));
    return;
  }

  try {
    const result = await withHibp.checkAsync(password);
    const match = result.sequence.find((entry) => entry.pattern === 'pwned');
    process.stdout.write(JSON.stringify(normalizeResult(result, {
      pwned: Boolean(match),
      pwnedCount: match?.pwnedAmount ?? (match ? 0 : null),
      hibpStatus: match ? 'pwned' : 'clean',
    })));
  } catch (error) {
    // Fail closed: still return the zxcvbn score, but tell the caller that
    // the breach status is unknown. The Python CLI maps this to exit 5.
    const result = withoutHibp.check(password);
    process.stdout.write(JSON.stringify(normalizeResult(result, {
      pwned: null,
      pwnedCount: null,
      hibpStatus: 'error',
      hibpError: error instanceof Error ? error.message : String(error),
    })));
  }
}

main().catch((error) => {
  process.stderr.write(error instanceof Error ? error.stack ?? error.message : String(error));
  process.exit(1);
});
