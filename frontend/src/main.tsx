import { QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./routes/App";
import { ActionFeedback } from "./components/ui/ActionFeedback";
import { queryClient } from "./lib/query/client";
import "@fontsource/fraunces/latin-400.css";
import "@fontsource/fraunces/latin-600.css";
import "@fontsource/public-sans/latin-400.css";
import "@fontsource/public-sans/latin-600.css";
import "@fontsource/public-sans/latin-700.css";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}><BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><App /><ActionFeedback /></BrowserRouter></QueryClientProvider>,
);
