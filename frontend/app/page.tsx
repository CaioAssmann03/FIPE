import { Header } from "@/components/Header";
import { ChatPanel } from "@/components/ChatPanel";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950">
      <Header />
      <div className="mx-auto max-w-6xl px-6 py-10 sm:px-8">
        <ChatPanel />
      </div>
    </main>
  );
}
