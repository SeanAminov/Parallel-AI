import { ThemeProvider } from "./context/ThemeContext";
import AppLayout from "./layouts/AppLayout";

export default function App() {
  return (
    <ThemeProvider>
      <AppLayout />
    </ThemeProvider>
  );
}
