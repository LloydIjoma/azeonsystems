interface Plan {
  name: string;
  // Matches the `plan` values register/page.tsx and /api/signup accept.
  // "custom" is not self-serve, so it has no signup plan key.
  planKey?: "starter" | "professional" | "enterprise";
  price: string;
  priceSuffix?: string;
  seats: string;
  features: string[];
  featured?: boolean;
  cta: string;
}

const PLANS: Plan[] = [
  {
    name: "Starter",
    planKey: "starter",
    price: "#0",
    priceSuffix: "/mo",
    seats: "Up to 3 users",
    features: ["Basic CRM & HR", "100 invoices/mo", "Community support"],
    cta: "Get started free",
  },
  {
    name: "Professional",
    planKey: "professional",
    price: "#50,000",
    priceSuffix: "/user/mo",
    seats: "Up to 15 users",
    features: ["HR, CRM & billing", "Unlimited invoices", "Priority email support"],
    featured: true,
    cta: "Start free trial",
  },
  {
    name: "Enterprise",
    planKey: "enterprise",
    price: "#90,000",
    priceSuffix: "/user/mo",
    seats: "Up to 50 users",
    features: ["All 5 core modules", "Advanced workflows", "API access"],
    cta: "Start free trial",
  },
  {
    name: "Custom",
    price: "Custom",
    seats: "Unlimited users",
    features: ["Custom integrations & SSO", "Dedicated account manager", "99.99% uptime SLA"],
    cta: "Contact sales",
  },
];

export default function PricingTable() {
  return (
    <section id="pricing" className="bg-gray-50 px-6 py-20">
      <div className="mx-auto max-w-7xl text-center">
        <h2 className="font-heading text-3xl font-bold text-azeon-navy sm:text-4xl">
          Simple, Scalable Pricing
        </h2>
        <p className="mx-auto mt-4 max-w-2xl font-body text-gray-600">
          Start free and scale up as your team grows — no hidden fees, cancel anytime.
        </p>

        <div className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-4">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`relative flex flex-col rounded-2xl border p-8 text-left shadow-sm ${
                plan.featured
                  ? "border-azeon-orange bg-white ring-2 ring-azeon-orange"
                  : "border-gray-200 bg-white"
              }`}
            >
              {plan.featured && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-azeon-orange px-3 py-1 font-body text-xs font-semibold uppercase tracking-wide text-white">
                  Most Popular
                </span>
              )}

              <h3 className="font-heading text-xl font-bold text-azeon-navy">{plan.name}</h3>
              <p className="mt-4 font-heading text-3xl font-extrabold text-gray-900 sm:text-4xl">
                {plan.price}
                {plan.priceSuffix && (
                  <span className="font-body text-sm font-medium text-gray-500">{plan.priceSuffix}</span>
                )}
              </p>
              <p className="mt-2 font-body text-sm font-semibold text-azeon-navy">{plan.seats}</p>

              <ul className="mt-6 flex-1 space-y-3">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 font-body text-sm text-gray-700">
                    <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-azeon-orange" />
                    {f}
                  </li>
                ))}
              </ul>

              <a
                href={plan.planKey ? `/register?plan=${plan.planKey}` : "#demo"}
                className={`mt-8 block rounded-md px-4 py-3 text-center font-body text-sm font-semibold transition ${
                  plan.featured
                    ? "bg-azeon-orange text-white hover:bg-azeon-orange-dark"
                    : "bg-azeon-navy text-white hover:bg-azeon-navy-dark"
                }`}
              >
                {plan.cta}
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
