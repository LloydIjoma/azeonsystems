import Header from "@/components/Header";
import Hero from "@/components/Hero";
import ModuleCards from "@/components/ModuleCards";
import PricingTable from "@/components/PricingTable";
import Testimonials from "@/components/Testimonials";
import Footer from "@/components/Footer";

export default function HomePage() {
  return (
    <main>
      <Header />
      <Hero />
      <ModuleCards />
      <PricingTable />
      <Testimonials />
      <Footer />
    </main>
  );
}
