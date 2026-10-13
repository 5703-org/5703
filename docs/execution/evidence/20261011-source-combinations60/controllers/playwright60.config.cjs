const path = require('node:path');
const output = process.env.PROOF60_OUTPUT_DIR;
if (!output) throw new Error('PROOF60_OUTPUT_DIR is required.');
module.exports = {
  testDir: __dirname, testMatch: 'proof60.spec.ts', workers: 1, retries: 0,
  timeout: 45000, outputDir: path.join(output, 'browser-artifacts'),
  reporter: [['list'], ['json', { outputFile: path.join(output, 'proof60-browser-results.json') }]],
  use: { channel: 'msedge', headless: true, viewport: { width: 1440, height: 1000 },
    serviceWorkers: 'block', trace: 'off', screenshot: 'off' },
};
