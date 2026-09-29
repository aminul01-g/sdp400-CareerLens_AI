import { useEffect, useState } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import api from "@/api/client";

// Pages
import Index from "./pages/Index";
import About from "./pages/About";
import Features from "./pages/Features";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Quiz from "./pages/Quiz";
import Recommendations from "./pages/Recommendations";
import Feedback from "./pages/Feedback";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

// Layout wrapper for public pages
const PublicLayout = ({ children, currentUser }: { children: React.ReactNode, currentUser: any }) => (
  <div className="min-h-screen flex flex-col">
    <Header isAuthenticated={!!currentUser} userEmail={currentUser?.email} />
    <main className="flex-1">
      {children}
    </main>
    <Footer />
  </div>
);

// Layout wrapper for authenticated pages
const AuthenticatedLayout = ({ children, currentUser }: { children: React.ReactNode, currentUser: any }) => (
  <div className="min-h-screen flex flex-col">
    <Header isAuthenticated={!!currentUser} userEmail={currentUser?.email} />
    <main className="flex-1">
      {children}
    </main>
    <Footer />
  </div>
);

const App = () => {
  const [currentUser, setCurrentUser] = useState<any>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try { setCurrentUser(JSON.parse(storedUser)); } catch (e) { setCurrentUser(null); }
    }
    if (token) {
      // refresh user from API
      api.me(token).then((res:any) => {
        if (res && res.user) {
          setCurrentUser(res.user);
          localStorage.setItem('user', JSON.stringify(res.user));
        }
      }).catch(() => {
        // ignore
      });
    }
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Index />} />
            <Route path="/about" element={
              <PublicLayout currentUser={currentUser}>
                <About />
              </PublicLayout>
            } />
            <Route path="/features" element={
              <PublicLayout currentUser={currentUser}>
                <Features />
              </PublicLayout>
            } />
            <Route path="/login" element={
              <PublicLayout currentUser={currentUser}>
                <Login />
              </PublicLayout>
            } />
            <Route path="/register" element={
              <PublicLayout currentUser={currentUser}>
                <Register />
              </PublicLayout>
            } />
            
            {/* Authenticated routes */}
            <Route path="/dashboard" element={
              <AuthenticatedLayout currentUser={currentUser}>
                <Dashboard />
              </AuthenticatedLayout>
            } />
            <Route path="/quiz" element={
              <AuthenticatedLayout currentUser={currentUser}>
                <Quiz />
              </AuthenticatedLayout>
            } />
            <Route path="/recommendations" element={
              <AuthenticatedLayout currentUser={currentUser}>
                <Recommendations />
              </AuthenticatedLayout>
            } />
            <Route path="/feedback" element={
              <AuthenticatedLayout currentUser={currentUser}>
                <Feedback />
              </AuthenticatedLayout>
            } />
            
            {/* Catch-all route */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;