export default function Hero() {
  return (
    <section className="bg-gradient-to-b from-azeon-navy to-azeon-navy-dark px-6 py-24 text-center text-white sm:py-32">
      <div className="mx-auto max-w-4xl">
        <span className="inline-flex items-center rounded-full border border-azeon-orange/40 bg-white/10 px-4 py-1.5 font-body text-xs font-semibold uppercase tracking-widest text-azeon-orange">
          Enterprise Resource Suite
        </span>

        <h1 className="mt-6 font-heading text-4xl font-extrabold leading-tight sm:text-6xl">
          Your Business, Seamlessly Connected.
        </h1>

        <p className="mx-auto mt-6 max-w-2xl font-body text-lg text-white/80">
          Azeon Systems unifies HR, Finance, CRM, and Inventory into a single integrated
          suite — so every department works from the same real-time data, and your
          leadership team gets a live view of the entire business.
        </p>

        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <a
            href="/register"
            className="inline-block w-full rounded-md bg-azeon-orange px-8 py-4 font-body text-base font-semibold text-white shadow-lg transition hover:bg-azeon-orange-dark sm:w-auto"
          >
            Sign Up Now - Start Free Trial
          </a>
          <a
            href="#demo"
            className="inline-block w-full rounded-md border-2 border-white/30 bg-transparent px-8 py-4 font-body text-base font-semibold text-white transition hover:border-white hover:bg-white/10 sm:w-auto"
          >
            Book a Demo
          </a>
        </div>
      </div>
    </section>
  );
}
