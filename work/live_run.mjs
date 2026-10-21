// Live runs for X_in and X_div, reusing KALPANG's authorize/execute/observe path (retargeted copy).
//   node live_run.mjs authorize <X_in|X_div>   -> request.json, authorization.json (no token needed)
//   node live_run.mjs execute   <X_in|X_div>   -> executes via the pinned GitHub MCP server, observes via REST
// The token is read from GITHUB_PERSONAL_ACCESS_TOKEN only. There is no `gh auth token` fallback.
// Raw comment bodies never reach disk: records carry SHA-256 hashes and lengths.
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { OWNER, REPO, ISSUE, BODIES } from './bodies.mjs';
import { createGitHubCommentAuthorization, assertGitHubCommentAuthorization, GITHUB_MCP_SERVER_IMAGE, GITHUB_MCP_TOOLSET } from './kalpang_run/src/github-comment-binding.js';
import { callGitHubMcp, executeAuthorizedGitHubComment } from './kalpang_run/src/execute-github-comment.js';
import { createGitHubRestObserver } from './kalpang_run/src/github-rest-observer.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const sha = (s) => createHash('sha256').update(s, 'utf8').digest('hex');
const [mode, label] = process.argv.slice(2);
if (!['authorize', 'execute'].includes(mode) || !BODIES[label]) {
  throw new Error('usage: live_run.mjs <authorize|execute> <X_in|X_div>');
}
const dir = path.join(here, 'artifacts', label);
await fs.mkdir(dir, { recursive: true });
const write = (name, value) => fs.writeFile(path.join(dir, name), `${JSON.stringify(value, null, 2)}\n`);

// The request carries the raw body in memory only; the file written to disk replaces it by its hash.
const makeRequest = () => ({
  jsonrpc: '2.0',
  method: 'tools/call',
  params: { name: 'add_issue_comment', arguments: { owner: OWNER, repo: REPO, issue_number: ISSUE, body: BODIES[label].authorized } },
});

if (mode === 'authorize') {
  const toAuthorize = makeRequest();
  const decisionRecord = createGitHubCommentAuthorization(toAuthorize, 'ALLOW');
  await write('authorization.json', decisionRecord);
  await write('request.sanitized.json', { ...toAuthorize, params: { ...toAuthorize.params, arguments: { ...toAuthorize.params.arguments, body: undefined, body_sha256: sha(toAuthorize.params.arguments.body), body_length: toAuthorize.params.arguments.body.length } } });
  console.log(`${label}: authorized, canonical_request_sha256=${decisionRecord.canonical_request_sha256}`);
} else {
  const token = process.env.GITHUB_PERSONAL_ACCESS_TOKEN;
  if (!token) throw new Error('GITHUB_PERSONAL_ACCESS_TOKEN is not set (no fallback is used)');
  const plannedRequest = makeRequest();
  const storedDecision = JSON.parse(await fs.readFile(path.join(dir, 'authorization.json'), 'utf8'));
  // refuses to continue unless the stored decision binds to exactly this request
  assertGitHubCommentAuthorization(plannedRequest, storedDecision);

  const rest = createGitHubRestObserver({ token });
  const seen = {};
  const restObserver = {
    async listIssueComments(r) {
      const list = await rest.listIssueComments(r);
      (seen.before ? (seen.after = list) : (seen.before = list));
      return list;
    },
    async getComment(r, id) { return (seen.detail = await rest.getComment(r, id)); },
  };
  const transported = BODIES[label].transported;
  const mcpMeta = {};
  const mcpCall = async (authorized) => {
    const sent = transported === authorized.params.arguments.body ? authorized
      : { ...authorized, params: { ...authorized.params, arguments: { ...authorized.params.arguments, body: transported } } };
    mcpMeta.transport_body_sha256 = sha(sent.params.arguments.body);
    const response = await callGitHubMcp(sent, token);
    mcpMeta.is_error = Boolean(response?.isError);
    return response;
  };

  const report = await executeAuthorizedGitHubComment({ request: plannedRequest, authorization: storedDecision, mcpCall, restObserver });
  const d = seen.detail;
  const bundle = {
    label,
    target: `${OWNER}/${REPO}#${ISSUE}`,
    mcp_server: { image: GITHUB_MCP_SERVER_IMAGE, toolset: GITHUB_MCP_TOOLSET },
    authorization: { decision: storedDecision.decision, canonical_request_sha256: storedDecision.canonical_request_sha256 },
    authorized_body_sha256: sha(BODIES[label].authorized),
    mcp: mcpMeta,
    rest_ids_before: (seen.before || []).map((c) => c.id),
    rest_ids_after: (seen.after || []).map((c) => c.id),
    observation: d ? {
      comment_id: d.id, node_id: d.node_id, issue_url: d.issue_url,
      body_sha256: sha(d.body), body_length: d.body.length,
      created_at: d.created_at, updated_at: d.updated_at,
    } : null,
    kalpang_report: report,
  };
  await write('live_bundle.json', bundle);
  console.log(JSON.stringify({ label, comparison_result: report.comparison_result, final_status: report.final_status, comment_id: report.observed_comment_id ?? null }));
}
