import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { 
  GraduationCap, 
  Menu, 
  X, 
  User, 
  LogOut,
  Settings,
  BarChart3
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface HeaderProps {
  isAuthenticated?: boolean;
  isAdmin?: boolean;
  userEmail?: string;
}

export const Header = ({ isAuthenticated = false, isAdmin = false, userEmail }: HeaderProps) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    // clear stored auth and navigate to home
    try { localStorage.removeItem('token'); localStorage.removeItem('user'); } catch(e) {}
    navigate("/");
  };

  const navLinks = [
    { name: "Home", path: "/" },
    { name: "About", path: "/about" },
    { name: "Features", path: "/features" },
  ];

  const userNavLinks = [
    { name: "Dashboard", path: "/dashboard" },
    { name: "Quiz", path: "/quiz" },
    { name: "Recommendations", path: "/recommendations" },
    { name: "Feedback", path: "/feedback" },
  ];

  const adminNavLinks = [
    { name: "Admin Dashboard", path: "/admin" },
    { name: "Analytics", path: "/admin/analytics" },
    { name: "Manage Questions", path: "/admin/questions" },
  ];

  const currentNavLinks = isAuthenticated ? (isAdmin ? adminNavLinks : userNavLinks) : navLinks;

  return (
    <header className="bg-card border-b border-border shadow-sm sticky top-0 z-50">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2 group">
            <div className="p-2 bg-gradient-to-r from-primary to-secondary rounded-lg group-hover:shadow-lg transition-all duration-300">
              <GraduationCap className="h-6 w-6 text-white" />
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              CareerGuide AI
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-8">
            {currentNavLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={`text-sm font-medium transition-colors hover:text-primary ${
                  location.pathname === link.path
                    ? "text-primary border-b-2 border-primary"
                    : "text-muted-foreground"
                }`}
              >
                {link.name}
              </Link>
            ))}
          </nav>

          {/* Desktop Auth Buttons */}
          <div className="hidden md:flex items-center space-x-4">
            {isAuthenticated ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="flex items-center space-x-2">
                    <User className="h-4 w-4" />
                    <span className="max-w-32 truncate">{userEmail || "User"}</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuItem onClick={() => navigate("/profile")}>
                    <Settings className="mr-2 h-4 w-4" />
                    Profile Settings
                  </DropdownMenuItem>
                  {isAdmin && (
                    <DropdownMenuItem onClick={() => navigate("/admin")}>
                      <BarChart3 className="mr-2 h-4 w-4" />
                      Admin Dashboard
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="text-destructive">
                    <LogOut className="mr-2 h-4 w-4" />
                    Sign Out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <>
                <Button variant="ghost" asChild>
                  <Link to="/login">Sign In</Link>
                </Button>
                <Button variant="hero" asChild>
                  <Link to="/register">Get Started</Link>
                </Button>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              {isMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden py-4 space-y-2 border-t border-border">
            {currentNavLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={`block py-2 text-sm font-medium transition-colors hover:text-primary ${
                  location.pathname === link.path
                    ? "text-primary"
                    : "text-muted-foreground"
                }`}
                onClick={() => setIsMenuOpen(false)}
              >
                {link.name}
              </Link>
            ))}
            
            <div className="pt-4 space-y-2 border-t border-border">
              {isAuthenticated ? (
                <>
                  <div className="flex items-center space-x-2 py-2">
                    <User className="h-4 w-4" />
                    <span className="text-sm font-medium">{userEmail || "User"}</span>
                  </div>
                  <Button
                    variant="ghost"
                    className="w-full justify-start"
                    onClick={() => { navigate("/profile"); setIsMenuOpen(false); }}
                  >
                    <Settings className="mr-2 h-4 w-4" />
                    Profile Settings
                  </Button>
                  {isAdmin && (
                    <Button
                      variant="ghost"
                      className="w-full justify-start"
                      onClick={() => { navigate("/admin"); setIsMenuOpen(false); }}
                    >
                      <BarChart3 className="mr-2 h-4 w-4" />
                      Admin Dashboard
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    className="w-full justify-start text-destructive"
                    onClick={() => { handleLogout(); setIsMenuOpen(false); }}
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    Sign Out
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    variant="ghost"
                    className="w-full justify-start"
                    asChild
                  >
                    <Link to="/login" onClick={() => setIsMenuOpen(false)}>
                      Sign In
                    </Link>
                  </Button>
                  <Button
                    variant="hero"
                    className="w-full"
                    asChild
                  >
                    <Link to="/register" onClick={() => setIsMenuOpen(false)}>
                      Get Started
                    </Link>
                  </Button>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  );
};