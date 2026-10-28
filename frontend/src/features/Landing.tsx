import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Aperture,
  Heart,
  MessageCircle,
  Sparkles,
} from "lucide-react";
import { Brand } from "../components/ui";
export default function Landing() {
  return (
    <div className="landing">
      <header>
        <Brand />
        <nav>
          <Link to="/login">Sign in</Link>
          <Link className="button small" to="/signup">
            Join Luma <ArrowUpRight size={16} />
          </Link>
        </nav>
      </header>
      <main>
        <div className="landing-copy">
          <span className="eyebrow">
            <span className="live-dot" /> LESS SCROLLING. MORE CONNECTING.
          </span>
          <h1>
            Life looks better
            <br />
            with a little
            <br />
            <em>perspective.</em>
          </h1>
          <p>
            A place for the big adventures, the small discoveries,
            <br className="desktop" /> and the people who make it all mean
            something.
          </p>
          <Link className="button" to="/signup">
            Find your people <ArrowUpRight size={20} />
          </Link>
          <small>Share a moment. Start a conversation. Be yourself.</small>
        </div>
        <div
          className="landing-art"
          aria-label="Abstract illustration of a sunlit landscape"
        >
          <div className="art-label">
            <Sparkles size={17} /> THE EVERYDAY, SEEN DIFFERENTLY.
          </div>
          <div className="landscape">
            <div className="sun" />
            <div className="mountain mountain-back" />
            <div className="mountain mountain-front" />
            <div className="landscape-caption">
              Somewhere
              <br />
              <em>worth sharing.</em>
            </div>
            <span>35° N · GOOD COMPANY</span>
          </div>
          <div className="floating-note">
            <Aperture size={30} />
            <div>
              <strong>Stay curious.</strong>
              <small>There’s a whole world out there.</small>
            </div>
          </div>
          <div className="floating-reactions">
            <Heart size={23} />
            <MessageCircle size={23} />
            <span>Little moments, real connections.</span>
          </div>
        </div>
      </main>
      <footer>
        <span>01 &nbsp; SHARE YOUR PERSPECTIVE</span>
        <span>02 &nbsp; FIND YOUR COMMUNITY</span>
        <span>03 &nbsp; KEEP IN TOUCH</span>
      </footer>
    </div>
  );
}
