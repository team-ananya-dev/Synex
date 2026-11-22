import { Instrument_Serif } from "next/font/google";
import { Landing } from "@/components/landing/Landing";

// Landing page over a live pixel koi pond (web/src/components/landing/).
// Instrument Serif for headlines; body and controls use Geist from the root layout.
const serif = Instrument_Serif({ weight: "400", style: ["normal", "italic"], subsets: ["latin"], variable: "--font-instrument" });

export default function Home() {
  return (
    <div className={serif.variable}>
      <Landing />
    </div>
  );
}
