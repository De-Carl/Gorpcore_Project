import Hero from "./sections/Hero";
import Direction from "./sections/Direction";
import TrendSignals from "./sections/TrendSignals";
import TrendAtlas from "./sections/TrendAtlas";
import Recommendations from "./sections/Recommendations";
import EvidenceGallery from "./sections/EvidenceGallery";
import Footer from "./sections/Footer";
import ScrollProgress from "./components/ScrollProgress";
import Marquee from "./components/Marquee";
import ScrollScene from "./components/ScrollScene";

export default function App() {
  return (
    <main>
      <ScrollProgress />
      <Hero />
      <Marquee />
      <ScrollScene variant="rise">
        <Direction />
      </ScrollScene>
      <ScrollScene variant="card">
        <TrendSignals />
      </ScrollScene>
      <ScrollScene variant="card">
        <TrendAtlas />
      </ScrollScene>
      <ScrollScene variant="rise">
        <Recommendations />
      </ScrollScene>
      <EvidenceGallery />
      <Marquee dark />
      <Footer />
    </main>
  );
}
