// Tiny build step, only for Vercel deploys: writes the API_BASE_URL
// environment variable (set in the Vercel dashboard, Settings -> Environment
// Variables) into assets/js/config.js so the deployed frontend knows where
// the backend (on Render) actually lives. No bundler, no dependencies - this
// project intentionally has none.
const fs = require("fs");
const path = require("path");

const apiBaseUrl = process.env.API_BASE_URL || "";

const output = `// Auto-generated at build time from the API_BASE_URL environment variable.
window.API_BASE_URL = ${JSON.stringify(apiBaseUrl)};
`;

const target = path.join(__dirname, "assets", "js", "config.js");
fs.writeFileSync(target, output);

console.log(
  `[build.js] wrote ${target} with API_BASE_URL = ${apiBaseUrl ? apiBaseUrl : "(empty - same-origin requests)"}`
);
