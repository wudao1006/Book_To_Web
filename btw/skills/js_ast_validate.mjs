import fs from "node:fs";
import { createRequire } from "node:module";

const requireFromFrontend = createRequire(
  new URL("../frontend/package.json", import.meta.url),
);
const parser = requireFromFrontend("@babel/parser");

const filePath = process.argv[2];
if (!filePath) {
  process.stdout.write(JSON.stringify({ valid: false, issues: ["missing_code_path"] }));
  process.exit(0);
}

const code = fs.readFileSync(filePath, "utf8");
const issues = [];

const allowedImports = new Set([
  "react",
]);
const blockedIdentifiers = new Set([
  "window",
  "document",
  "globalThis",
  "localStorage",
  "sessionStorage",
]);
const blockedCalls = new Set(["eval", "Function", "fetch", "XMLHttpRequest"]);

function memberName(node) {
  if (!node || node.type !== "MemberExpression") {
    return null;
  }
  const object = node.object?.type === "Identifier" ? node.object.name : null;
  const property =
    node.property?.type === "Identifier"
      ? node.property.name
      : node.property?.type === "StringLiteral"
        ? node.property.value
        : null;
  if (!object || !property) {
    return null;
  }
  return `${object}.${property}`;
}

function walk(node, parent = null) {
  if (!node || typeof node !== "object") {
    return;
  }

  if (node.type === "ImportDeclaration") {
    const source = node.source?.value;
    if (typeof source === "string" && !allowedImports.has(source)) {
      issues.push(`import_not_allowed:${source}`);
    }
  }

  if (node.type === "ImportExpression") {
    issues.push("dynamic_import_blocked");
  }

  if (node.type === "CallExpression") {
    if (node.callee?.type === "Identifier" && blockedCalls.has(node.callee.name)) {
      const code = node.callee.name === "fetch" ? "network_call_blocked:fetch" : `call_blocked:${node.callee.name}`;
      issues.push(code);
    }
    if (node.callee?.type === "MemberExpression") {
      const name = memberName(node.callee);
      if (name === "globalThis.fetch" || name === "window.fetch") {
        issues.push("network_call_blocked:fetch");
      }
    }
  }

  if (node.type === "NewExpression" && node.callee?.type === "Identifier") {
    if (blockedCalls.has(node.callee.name)) {
      issues.push(`constructor_blocked:${node.callee.name}`);
    }
  }

  if (node.type === "Identifier" && blockedIdentifiers.has(node.name)) {
    if (!(parent && parent.type === "MemberExpression" && parent.property === node && !parent.computed)) {
      issues.push(`sensitive_global_blocked:${node.name}`);
    }
  }

  if (node.type === "MemberExpression") {
    const name = memberName(node);
    if (
      name === "document.cookie" ||
      name === "window.document" ||
      name === "window.localStorage" ||
      name === "window.sessionStorage"
    ) {
      issues.push(`sensitive_member_blocked:${name}`);
    }
  }

  for (const value of Object.values(node)) {
    if (Array.isArray(value)) {
      for (const child of value) {
        if (child && typeof child === "object") {
          walk(child, node);
        }
      }
      continue;
    }
    if (value && typeof value === "object" && "type" in value) {
      walk(value, node);
    }
  }
}

try {
  const ast = parser.parse(code, {
    sourceType: "module",
    plugins: ["jsx", "typescript"],
  });
  walk(ast);
} catch (error) {
  issues.push(`ast_parse_failed:${String(error.message || error)}`);
}

const uniqueIssues = Array.from(new Set(issues));
process.stdout.write(
  JSON.stringify({
    valid: uniqueIssues.length === 0 && code.trim().length > 0,
    issues: uniqueIssues.length === 0 ? [] : uniqueIssues,
  }),
);
