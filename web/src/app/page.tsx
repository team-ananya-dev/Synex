import { Pixelify_Sans, Silkscreen } from "next/font/google";
import { Landing } from "@/components/landing/Landing";

// Landing page over a live pixel koi pond (web/src/components/landing/).
// Silkscreen for the big display type, Pixelify Sans for labels and buttons.
const pixel = Pixelify_Sans({ subsets: ["latin"], variable: "--font-pixelify" });
const display = Silkscreen({ weight: ["400", "700"], subsets: ["latin"], variable: "--font-silkscreen" });

export default function Home() {
  return (
    <div className={`${pixel.variable} ${display.variable}`}>
      <Landing />
    </div>
  );
}
