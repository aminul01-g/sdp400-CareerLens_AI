import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import Landing from "./Landing";

const Index = () => {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1">
        <Landing />
      </main>
      <Footer />
    </div>
  );
};

export default Index;
