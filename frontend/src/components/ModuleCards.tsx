const MODULES = [
  {
    name: "HR Management",
    description: "Onboarding, attendance, employee records, and performance tracking in one place.",
  },
  {
    name: "Finance & Accounting",
    description: "General ledger, expenses, and real-time cash flow visibility built in.",
  },
  {
    name: "CRM & Sales",
    description: "Track leads, deals, and customer relationships across the full pipeline.",
  },
  {
    name: "Inventory Control",
    description: "Real-time stock levels, valuation, and fulfillment across every warehouse.",
  },
  {
    name: "Integrated Billing",
    description: "Automated invoicing and subscription billing that syncs directly with Finance.",
  },
];

export default function ModuleCards() {
  return (
    <section id="modules" className="mx-auto max-w-7xl px-6 py-20">
      <h2 className="text-center font-heading text-3xl font-bold text-azeon-navy sm:text-4xl">
        Everything Your Enterprise Needs
      </h2>
      <p className="mx-auto mt-4 max-w-2xl text-center font-body text-gray-600">
        Five core modules, one connected platform — no more switching tools or
        reconciling data between systems.
      </p>
      <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-5">
        {MODULES.map((mod) => (
          <div
            key={mod.name}
            className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
          >
            <div className="mb-4 h-2 w-10 rounded-full bg-azeon-orange" />
            <h3 className="font-heading text-lg font-bold text-azeon-navy">{mod.name}</h3>
            <p className="mt-2 font-body text-sm text-gray-600">{mod.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
