import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Dashboard } from "./pages/Dashboard";
import { CanvasPage } from "./pages/CanvasPage";
import { HubPage } from "./pages/HubPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/canvas/:id" element={<CanvasPage />} />
        <Route path="/hub" element={<HubPage />} />
      </Routes>
    </BrowserRouter>
  );
}
