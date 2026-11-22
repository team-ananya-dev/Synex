import { VT323 } from "next/font/google";
import { Landing } from "@/components/landing/Landing";

// Landing page: an interactive dive through Synex's eight stages (web/src/components/landing/).
const pixel = VT323({ weight: "400", subsets: ["latin"], variable: "--font-vt323" });

export default function Home() {
  return (
    <div className={pixel.variable}>
      <Landing />
    </div>
  );
}
