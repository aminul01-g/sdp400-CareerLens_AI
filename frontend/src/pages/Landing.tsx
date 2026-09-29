import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { 
  Brain, 
  Target, 
  BarChart3, 
  Users, 
  CheckCircle, 
  ArrowRight,
  Star,
  Sparkles,
  TrendingUp
} from "lucide-react";

export default function Landing() {
  const features = [
    {
      icon: Brain,
      title: "AI-Powered Analysis",
      description: "Advanced machine learning algorithms analyze your interests, personality, and academic performance to provide personalized career recommendations."
    },
    {
      icon: Target,
      title: "Personalized Recommendations",
      description: "Get tailored career paths based on your unique profile, with detailed insights into required skills and educational pathways."
    },
    {
      icon: BarChart3,
      title: "Detailed Analytics",
      description: "Comprehensive reports with confidence scores, salary ranges, and growth projections for each recommended career path."
    },
    {
      icon: Users,
      title: "Expert Guidance",
      description: "Access to career counselors and industry experts who can provide additional insights and mentorship."
    }
  ];

  const testimonials = [
    {
      name: "Sarah Johnson",
      role: "Computer Science Student",
      content: "CareerGuide AI helped me discover my passion for UX design. The recommendations were spot-on and gave me a clear path forward.",
      rating: 5
    },
    {
      name: "Michael Chen",
      role: "Business Major",
      content: "I was unsure about my career direction until I used this platform. Now I'm confident about pursuing data analytics.",
      rating: 5
    },
    {
      name: "Emily Rodriguez",
      role: "High School Senior",
      content: "The detailed career analysis helped me choose my college major with confidence. Highly recommended!",
      rating: 5
    }
  ];

  const steps = [
    {
      step: 1,
      title: "Take the Assessment",
      description: "Complete our comprehensive quiz covering your interests, personality traits, and academic strengths."
    },
    {
      step: 2,
      title: "AI Analysis",
      description: "Our advanced algorithms analyze your responses and match them with thousands of career profiles."
    },
    {
      step: 3,
      title: "Get Recommendations",
      description: "Receive personalized career suggestions with detailed insights and actionable next steps."
    }
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative py-20 lg:py-32 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-secondary/5 to-accent/5"></div>
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="text-center max-w-4xl mx-auto">
            <div className="inline-flex items-center px-4 py-2 bg-muted rounded-full text-sm font-medium text-muted-foreground mb-6">
              <Sparkles className="h-4 w-4 mr-2" />
              AI-Powered Career Guidance Platform
            </div>
            
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-foreground mb-6">
              Discover Your
              <span className="block bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent">
                Perfect Career Path
              </span>
            </h1>
            
            <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
              Leverage the power of AI to analyze your interests, personality, and academic strengths. 
              Get personalized career recommendations that align with your unique profile.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button variant="hero" size="hero" asChild className="group">
                <Link to="/register">
                  Start Your Journey
                  <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                </Link>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <Link to="/about">Learn More</Link>
              </Button>
            </div>
            
            <div className="mt-12 flex items-center justify-center space-x-8 text-sm text-muted-foreground">
              <div className="flex items-center">
                <CheckCircle className="h-4 w-4 text-success mr-2" />
                Free to use
              </div>
              <div className="flex items-center">
                <CheckCircle className="h-4 w-4 text-success mr-2" />
                Instant results
              </div>
              <div className="flex items-center">
                <CheckCircle className="h-4 w-4 text-success mr-2" />
                Expert-backed
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              Why Choose CareerGuide AI?
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Our platform combines cutting-edge AI technology with career expertise to provide you with the most accurate and actionable guidance.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <Card key={index} className="group hover:shadow-lg transition-all duration-300 hover:-translate-y-2">
                <CardContent className="p-6 text-center">
                  <div className="inline-flex items-center justify-center w-12 h-12 bg-gradient-to-r from-primary to-secondary rounded-lg mb-4 group-hover:scale-110 transition-transform">
                    <feature.icon className="h-6 w-6 text-white" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-muted-foreground">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              How It Works
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Get started with your career discovery journey in just three simple steps.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {steps.map((step, index) => (
              <div key={index} className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-primary to-secondary rounded-full text-white text-xl font-bold mb-4">
                  {step.step}
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-2">
                  {step.title}
                </h3>
                <p className="text-muted-foreground">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              What Students Say
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Hear from students who have transformed their career journey with CareerGuide AI.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <Card key={index} className="hover:shadow-lg transition-all duration-300">
                <CardContent className="p-6">
                  <div className="flex items-center mb-4">
                    {Array.from({ length: testimonial.rating }).map((_, i) => (
                      <Star key={i} className="h-4 w-4 text-warning fill-current" />
                    ))}
                  </div>
                  <p className="text-muted-foreground mb-4 italic">
                    "{testimonial.content}"
                  </p>
                  <div>
                    <p className="font-semibold text-foreground">{testimonial.name}</p>
                    <p className="text-sm text-muted-foreground">{testimonial.role}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              Trusted by Students Worldwide
            </h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="text-4xl font-bold text-primary mb-2">10K+</div>
              <p className="text-muted-foreground">Students Guided</p>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-secondary mb-2">95%</div>
              <p className="text-muted-foreground">Satisfaction Rate</p>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-accent mb-2">500+</div>
              <p className="text-muted-foreground">Career Paths</p>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-success mb-2">24/7</div>
              <p className="text-muted-foreground">Support Available</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-primary via-secondary to-accent">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Ready to Discover Your Future?
          </h2>
          <p className="text-xl text-white/90 mb-8 max-w-2xl mx-auto">
            Join thousands of students who have found their perfect career path with our AI-powered guidance system.
          </p>
          <Button variant="outline" size="hero" className="bg-white text-primary hover:bg-white/90" asChild>
            <Link to="/register">
              Get Started for Free
              <TrendingUp className="ml-2 h-5 w-5" />
            </Link>
          </Button>
        </div>
      </section>
    </div>
  );
}