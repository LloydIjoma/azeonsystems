const FOOTER_COLUMNS = [
  {
    heading: "Product",
    links: [
      { label: "HR Management", href: "#modules" },
      { label: "Finance & Accounting", href: "#modules" },
      { label: "CRM & Sales", href: "#modules" },
      { label: "Inventory Control", href: "#modules" },
      { label: "Pricing", href: "#pricing" },
    ],
  },
  {
    heading: "Company",
    links: [
      { label: "About Us", href: "/about" },
      { label: "Careers", href: "/careers" },
      { label: "Blog", href: "/blog" },
      { label: "Partners", href: "/partners" },
    ],
  },
  {
    heading: "Resources",
    links: [
      { label: "Documentation", href: "/docs" },
      { label: "API Reference", href: "/docs/api" },
      { label: "Security", href: "/security" },
      { label: "Status", href: "/status" },
    ],
  },
  {
    heading: "Legal",
    links: [
      { label: "Privacy Policy", href: "/privacy" },
      { label: "Terms of Service", href: "/terms" },
      { label: "SLA", href: "/sla" },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="bg-azeon-navy px-6 pb-8 pt-16 text-white/70">
      <div className="mx-auto grid max-w-7xl grid-cols-2 gap-8 sm:grid-cols-3 lg:grid-cols-5">
        <div className="col-span-2 sm:col-span-3 lg:col-span-1">
          <p className="font-heading text-xl font-extrabold tracking-tight text-white">
            Azeon<span className="text-azeon-orange">Systems</span>
          </p>
          <p className="mt-3 font-body text-sm text-white/60">
            The Enterprise Resource Suite connecting HR, Finance, CRM, and Inventory.
          </p>
          <div className="mt-4 space-y-1 font-body text-sm">
            <p>
              <a href="mailto:support@azeonsystems.com.ng" className="hover:text-white">
                support@azeonsystems.com.ng
              </a>
            </p>
            <p>
              <a href="tel:+18005552966" className="hover:text-white">
                +1 (800) 555-AZON
              </a>
            </p>
          </div>
        </div>

        {FOOTER_COLUMNS.map((col) => (
          <div key={col.heading}>
            <h3 className="font-heading text-sm font-bold uppercase tracking-wide text-white">
              {col.heading}
            </h3>
            <ul className="mt-4 space-y-2">
              {col.links.map((link) => (
                <li key={link.label}>
                  <a href={link.href} className="font-body text-sm text-white/70 hover:text-white">
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="mx-auto mt-12 max-w-7xl border-t border-white/10 pt-6 text-center">
        <p className="font-body text-sm text-white/60">
          © {new Date().getFullYear()} Azeon Systems. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
