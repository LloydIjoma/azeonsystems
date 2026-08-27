interface Testimonial {
  quote: string;
  name: string;
  title: string;
  company: string;
}

const TESTIMONIALS: Testimonial[] = [
  {
    quote:
      "Azeon Systems replaced four disconnected tools overnight. Our HR and Finance teams finally see the same numbers.",
    name: "Soren Marsh",
    title: "COO",
    company: "TechScale",
  },
  {
    quote:
      "The real-time dashboards changed how we run leadership meetings. We make decisions in minutes, not days.",
    name: "Elena Rostova",
    title: "CEO",
    company: "Nexa Cloud",
  },
  {
    quote:
      "Inventory Control alone paid for the platform. We cut fulfillment errors dramatically within the first quarter.",
    name: "Marcus Vance",
    title: "VP of Operations",
    company: "Apex Logistics",
  },
];

export default function Testimonials() {
  return (
    <section id="testimonials" className="mx-auto max-w-7xl px-6 py-20">
      <h2 className="text-center font-heading text-3xl font-bold text-azeon-navy sm:text-4xl">
        Trusted by Growing Enterprises
      </h2>
      <p className="mx-auto mt-4 max-w-2xl text-center font-body text-gray-600">
        See what leaders across industries are saying about running their business on
        Azeon Systems.
      </p>

      <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
        {TESTIMONIALS.map((t) => (
          <figure
            key={t.name}
            className="flex flex-col rounded-xl border border-gray-100 bg-white p-8 shadow-sm"
          >
            <div className="mb-4 h-2 w-10 rounded-full bg-azeon-orange" />
            <blockquote className="flex-1 font-body text-sm leading-relaxed text-gray-700">
              &ldquo;{t.quote}&rdquo;
            </blockquote>
            <figcaption className="mt-6 border-t border-gray-100 pt-4">
              <p className="font-heading text-sm font-bold text-azeon-navy">{t.name}</p>
              <p className="font-body text-xs text-gray-500">
                {t.title}, {t.company}
              </p>
            </figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}
