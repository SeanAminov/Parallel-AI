import { ThemeProvider } from "./context/ThemeContext";
import AppLayout from "./layouts/AppLayout";
import { TaskProvider } from "./context/TaskContext";

export default function App() {
  return (
    <ThemeProvider>
      <TaskProvider>
        <AppLayout />
      </TaskProvider>
    </ThemeProvider>
  );
}
