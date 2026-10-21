// GitHub-side tools for the witness experiment. Token: GITHUB_PERSONAL_ACCESS_TOKEN only.
//   fresh   <label> <comment_id> <out.json>      sanitized REST read + classification vs the canonical expected body
//   edit    <label> <comment_id> <out.json>      PATCH the comment back to the authorized body (cells E, A8+E)
//   history <comment_id> <out.json>              GraphQL userContentEdits (hashes/metadata only)
//   introspect <out.json>                        GraphQL: mutation/type names that mention edit/revision/history
//   purge   <comment_id> <edit_node_id> <mutation> <out.json>   attempt to delete one revision (A8+E probe)
// Raw bodies and diffs are never written; hashes, lengths and metadata are.
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import { OWNER, REPO, BODIES } from './bodies.mjs';

const token = process.env.GITHUB_PERSONAL_ACCESS_TOKEN;
if (!token) throw new Error('GITHUB_PERSONAL_ACCESS_TOKEN is not set (no fallback is used)');
const sha = (s) => createHash('sha256').update(s ?? '', 'utf8').digest('hex');
const H = { accept: 'application/vnd.github+json', authorization: `Bearer ${token}`, 'x-github-api-version': '2022-11-28' };
const [cmd, ...a] = process.argv.slice(2);
const save = (file, v) => fs.writeFile(file, `${JSON.stringify(v, null, 2)}\n`);
const url = (id) => `https://api.github.com/repos/${OWNER}/${REPO}/issues/comments/${id}`;
const gql = async (query, variables) => {
  const r = await fetch('https://api.github.com/graphql', { method: 'POST', headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' }, body: JSON.stringify({ query, variables }) });
  return { http: r.status, json: await r.json().catch(() => null) };
};
const sanitize = (d) => ({ comment_id: d.id, node_id: d.node_id, issue_url: d.issue_url, body_sha256: sha(d.body), body_length: d.body.length, created_at: d.created_at, updated_at: d.updated_at, author_association: d.author_association });

if (cmd === 'fresh') {
  const [label, id, out] = a;
  const r = await fetch(url(id), { headers: H });
  const readAt = new Date().toISOString();
  let rec;
  if (!r.ok) rec = { http: r.status, read_at_local: readAt, classification: 'INDETERMINATE', reason: `HTTP ${r.status}` };
  else {
    const s = sanitize(await r.json());
    const expected = sha(BODIES[label].authorized);
    rec = { http: 200, read_at_local: readAt, ...s, expected_body_sha256: expected, classification: s.body_sha256 === expected ? 'IN-BOUNDS' : 'DIVERGENT' };
  }
  await save(out, rec); console.log(JSON.stringify({ label, classification: rec.classification, updated_at: rec.updated_at, created_at: rec.created_at }));
} else if (cmd === 'edit') {
  const [label, id, out] = a;
  const r = await fetch(url(id), { method: 'PATCH', headers: { ...H, 'content-type': 'application/json' }, body: JSON.stringify({ body: BODIES[label].authorized }) });
  const rec = r.ok ? { http: r.status, edited_at_local: new Date().toISOString(), ...sanitize(await r.json()) } : { http: r.status };
  await save(out, rec); console.log(JSON.stringify({ http: rec.http, updated_at: rec.updated_at }));
} else if (cmd === 'history') {
  const [id, out] = a;
  const node = (await (await fetch(url(id), { headers: H })).json()).node_id;
  const q = `query($id:ID!){ node(id:$id){ ... on IssueComment { viewerDidAuthor includesCreatedEdit lastEditedAt
      userContentEdits(first:50){ totalCount nodes { id createdAt editedAt deletedAt deletedBy{login} editor{login} diff } } } } }`;
  const { http, json } = await gql(q, { id: node });
  const nodes = json?.data?.node?.userContentEdits?.nodes;
  const rec = {
    http, node_id: node, errors: json?.errors?.map((e) => ({ type: e.type, message: e.message })) ?? null,
    viewerDidAuthor: json?.data?.node?.viewerDidAuthor, includesCreatedEdit: json?.data?.node?.includesCreatedEdit, lastEditedAt: json?.data?.node?.lastEditedAt,
    totalCount: json?.data?.node?.userContentEdits?.totalCount ?? null,
    edits: nodes ? nodes.map((n) => ({ id: n.id, createdAt: n.createdAt, editedAt: n.editedAt, deletedAt: n.deletedAt, deletedBy: n.deletedBy?.login ?? null, editor: n.editor?.login ?? null, diff_sha256: n.diff == null ? null : sha(n.diff), diff_length: n.diff == null ? null : n.diff.length })) : null,
  };
  await save(out, rec); console.log(JSON.stringify({ http, totalCount: rec.totalCount, edits: rec.edits?.length ?? null, errors: rec.errors }));
} else if (cmd === 'introspect') {
  const [out] = a;
  const { http, json } = await gql(`{ __schema { mutationType { fields { name } } types { name } } }`);
  const re = /edit|revision|history/i;
  const rec = { http, errors: json?.errors ?? null,
    mutations_matching: json?.data?.__schema.mutationType.fields.map((f) => f.name).filter((n) => re.test(n)),
    types_matching: json?.data?.__schema.types.map((t) => t.name).filter((n) => re.test(n)) };
  await save(out, rec); console.log(JSON.stringify(rec));
} else if (cmd === 'purge') {
  const [, editId, mutation, out] = a;
  if (!/^[A-Za-z]+$/.test(mutation)) throw new Error('bad mutation name');
  const { http, json } = await gql(`mutation($id:ID!){ ${mutation}(input:{id:$id}){ clientMutationId } }`, { id: editId });
  const rec = { attempted_mutation: mutation, http, errors: json?.errors?.map((e) => ({ type: e.type, message: e.message })) ?? null, data: json?.data ?? null };
  await save(out, rec); console.log(JSON.stringify(rec));
} else throw new Error('unknown command');
