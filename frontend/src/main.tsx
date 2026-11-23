import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import "./styles/index.css";
import "./styles/discovery.css";
import "./styles/commercial.css";
import "./styles/navbar-search.css";
import "./styles/travel.css";
import "./styles/login-motion.css";
import "./styles/login-collage.css";
import "./styles/consumer-gallery.css";
import "./styles/consumer-motion.css";
import "./styles/guest.css";
import "./styles/branding.css";
import "./styles/chat.css";
import "./styles/sidebar.css";
import "./styles/profile.css";
import "./styles/comments.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);
