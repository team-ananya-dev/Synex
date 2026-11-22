import { Pixelify_Sans } from "next/font/google";
import { Landing } from "@/components/landing/Landing";

// Landing page over a live pixel koi pond (web/src/components/landing/).
const pixel = Pixelify_Sans({ subsets: ["latin"], variable: "--font-pixelify" });

export default function Home() {
  return (
    <div className={pixel.variable}>
      <Landing />
    </div>
  );
}
