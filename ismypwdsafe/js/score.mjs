import { zxcvbn, zxcvbnOptions } from '@zxcvbn-ts/core';
import * as common from '@zxcvbn-ts/language-common';
import * as en from '@zxcvbn-ts/language-en';

zxcvbnOptions.setOptions({
  dictionary: { ...common.dictionary, ...en.dictionary },
  graphs: common.adjacencyGraphs,
  translations: en.translations,
});

const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
const { password } = JSON.parse(Buffer.concat(chunks).toString('utf8'));
const r = zxcvbn(password);
process.stdout.write(JSON.stringify({
  score: r.score,
  guesses_log10: Math.log10(r.guesses),
  feedback: r.feedback,
}));