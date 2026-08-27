// Client-side mirror of provisioner/app.py's `slugify()`. This exists ONLY
// for the live subdomain preview on /register — the Python version in the
// provisioner is the actual source of truth enforced server-side, since a
// client can always send a raw company_name straight to /api/signup. Keep
// the two in sync if either changes.

const RESERVED_SLUGS = new Set([
  "www", "api", "app", "admin", "provisioner", "mail", "ftp", "smtp",
  "assets", "static", "cdn", "root", "system", "erpnext", "frappe",
  "billing", "status", "support", "docs", "blog",
]);

export interface SlugResult {
  slug: string;
  isValid: boolean;
  reason?: "empty" | "reserved" | "invalid";
}

export function slugify(companyName: string): SlugResult {
  const trimmed = companyName.trim().toLowerCase();
  if (!trimmed) return { slug: "", isValid: false, reason: "empty" };

  let slug = trimmed.replace(/[^a-z0-9]+/g, "-");
  slug = slug.replace(/-{2,}/g, "-").replace(/^-+|-+$/g, "");
  slug = slug.slice(0, 50).replace(/^-+|-+$/g, "");

  if (!slug) return { slug: "", isValid: false, reason: "empty" };
  if (RESERVED_SLUGS.has(slug)) return { slug, isValid: false, reason: "reserved" };
  if (!/^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/.test(slug)) {
    return { slug, isValid: false, reason: "invalid" };
  }

  return { slug, isValid: true };
}
