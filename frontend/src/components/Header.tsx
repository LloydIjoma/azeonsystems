import Link from "next/link";

const NAV_LINKS = [
  { label: "Modules", href: "#modules" },
  { label: "Pricing", href: "#pricing" },
  { label: "Customers", href: "#testimonials" },
];

export default function Header() {
  return (
    <header className="sticky top-0 z-50 bg-azeon-navy text-white shadow-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link href="/" className="font-heading text-xl font-extrabold tracking-tight">
          Azeon<span className="text-azeon-orange">Systems</span>
        </Link>

        <nav className="hidden gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="font-body text-sm font-semibold text-white/90 hover:text-white"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          {/* Sign In destination isn't built in this phase — wire to the
              real tenant login flow when it exists. */}
          <Link href="/login" className="font-body text-sm font-semibold text-white/90 hover:text-white">
            Sign In
          </Link>
          <a
            href="#demo"
            className="rounded-md border border-white/30 px-4 py-2 font-body text-sm font-semibold text-white transition hover:border-white hover:bg-white/10"
          >
            Book a Demo
          </a>
          <Link
            href="/register"
            className="rounded-md bg-azeon-orange px-4 py-2 font-body text-sm font-semibold text-white shadow-sm transition hover:bg-azeon-orange-dark"
          >
            Start Free Trial
          </Link>
        </div>
      </div>
    </header>
  );
}
