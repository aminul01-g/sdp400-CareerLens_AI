import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { 
  Brain, 
  ClipboardList, 
  Target, 
  FileText, 
  MessageSquare, 
  BarChart3,
  Users,
  Shield,
  Smartphone,
  Zap,
  Clock,
  Award,
  ChevronRight,
  CheckCircle
} from "lucide-react";

const Features = () => {
  const coreFeatures = [
    {
      icon: ClipboardList,
      title: "Interactive Career Assessment Quiz",
      description: "Comprehensive multi-step quiz analyzing interests, personality traits, academic strengths, and career preferences.",
      benefits: [
        "15-20 scientifically-backed questions",
        "Multiple question types (multiple choice, Likert scale)",
        "Progress tracking and save functionality",
        "Personalized difficulty adaptation"
      ],
      gradient: "from-blue-500 to-purple-600"
    },
    {
      icon: Brain,
      title: "AI-Powered Career Recommendations",
      description: "Advanced machine learning algorithms provide personalized career suggestions with confidence scores.",
      benefits: [
        "95%+ accuracy in career matching",
        "Real-time analysis of 500+ career paths",
        "Confidence scoring for each recommendation",
        "Industry trend integration"
      ],
      gradient: "from-purple-500 to-pink-600"
    },
    {
      icon: FileText,
      title: "Detailed Career Reports",
      description: "Comprehensive PDF reports with career insights, required skills, education paths, and salary expectations.",
      benefits: [
        "Professional PDF generation",
        "Detailed skill gap analysis",
        "Educational pathway recommendations",
        "Industry outlook and trends"
      ],
      gradient: "from-green-500 to-teal-600"
    },
    {
      icon: BarChart3,
      title: "Advanced Admin Dashboard",
      description: "Powerful analytics and management tools for educational institutions and administrators.",
      benefits: [
        "Real-time user analytics",
        "Quiz question management (CRUD)",
        "Student progress tracking",
        "Performance metrics and insights"
      ],
      gradient: "from-orange-500 to-red-600"
    }
  ];

  const additionalFeatures = [
    {
      icon: Users,
      title: "Multi-User Support",
      description: "Separate dashboards for students, counselors, and administrators"
    },
    {
      icon: Shield,
      title: "Data Security",
      description: "Enterprise-grade security with GDPR compliance"
    },
    {
      icon: Smartphone,
      title: "Mobile Responsive",
      description: "Optimized experience across all devices and screen sizes"
    },
    {
      icon: Zap,
      title: "Real-Time Analytics",
      description: "Live insights and performance metrics for institutions"
    },
    {
      icon: Clock,
      title: "24/7 Availability",
      description: "Always accessible career guidance platform"
    },
    {
      icon: Award,
      title: "Certification Ready",
      description: "Generates official career assessment certificates"
    }
  ];

  const benefits = [
    "Reduce counselor workload by 60%",
    "Increase student engagement by 92%",
    "Improve career satisfaction by 85%",
    "Save 40+ hours per semester on career guidance",
    "Access to 500+ career path database",
    "Evidence-based career recommendations"
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      {/* Hero Section */}
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16">
        <div className="text-center max-w-4xl mx-auto">
          <Badge variant="outline" className="mb-6 px-4 py-2">
            <Zap className="w-4 h-4 mr-2" />
            Platform Features
          </Badge>
          <h1 className="text-4xl lg:text-6xl font-bold mb-6">
            Powerful Features for{" "}
            <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              Smart Career Guidance
            </span>
          </h1>
          <p className="text-xl text-muted-foreground leading-relaxed mb-8">
            Discover how our AI-powered platform transforms career guidance with cutting-edge features 
            designed for students, counselors, and educational institutions.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" asChild>
              <Link to="/register">
                Try All Features Free <ChevronRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link to="/about">Learn More</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Core Features */}
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl lg:text-4xl font-bold mb-4">Core Features</h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            The essential tools that make our platform the leading choice for career guidance.
          </p>
        </div>

        <div className="space-y-12 max-w-6xl mx-auto">
          {coreFeatures.map((feature, index) => (
            <Card key={index} className={`overflow-hidden ${index % 2 === 1 ? 'lg:flex-row-reverse' : ''}`}>
              <div className="lg:flex">
                <div className="lg:w-1/2 p-8">
                  <div className={`p-3 bg-gradient-to-r ${feature.gradient} rounded-lg w-fit mb-4`}>
                    <feature.icon className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold mb-4">{feature.title}</h3>
                  <p className="text-muted-foreground mb-6 leading-relaxed">
                    {feature.description}
                  </p>
                  <div className="space-y-2">
                    {feature.benefits.map((benefit, benefitIndex) => (
                      <div key={benefitIndex} className="flex items-center">
                        <CheckCircle className="w-5 h-5 text-green-500 mr-3 flex-shrink-0" />
                        <span className="text-sm text-muted-foreground">{benefit}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className={`lg:w-1/2 bg-gradient-to-br ${feature.gradient} p-8 flex items-center justify-center`}>
                  <div className="text-center text-white">
                    <feature.icon className="w-24 h-24 mx-auto mb-4 opacity-80" />
                    <p className="text-lg font-medium opacity-90">Interactive Demo Available</p>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* Additional Features Grid */}
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl lg:text-4xl font-bold mb-4">Additional Features</h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Extended capabilities that enhance the complete career guidance experience.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {additionalFeatures.map((feature, index) => (
            <Card key={index} className="p-6 hover:shadow-lg transition-all duration-300 group">
              <CardHeader className="pb-4">
                <div className="p-3 bg-gradient-to-r from-primary/10 to-secondary/10 rounded-lg w-fit mb-3 group-hover:scale-110 transition-transform duration-300">
                  <feature.icon className="w-6 h-6 text-primary" />
                </div>
                <CardTitle className="text-lg">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <p className="text-muted-foreground text-sm">{feature.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Benefits Section */}
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="bg-gradient-to-r from-primary/5 to-secondary/5 rounded-2xl p-8 lg:p-12">
          <div className="grid lg:grid-cols-2 gap-8 items-center">
            <div>
              <h2 className="text-3xl lg:text-4xl font-bold mb-6">
                Why Choose Our Platform?
              </h2>
              <p className="text-muted-foreground text-lg mb-8">
                Our comprehensive feature set delivers measurable results for educational institutions 
                and transformative experiences for students.
              </p>
              <div className="space-y-3">
                {benefits.map((benefit, index) => (
                  <div key={index} className="flex items-center">
                    <CheckCircle className="w-5 h-5 text-green-500 mr-3 flex-shrink-0" />
                    <span className="text-muted-foreground">{benefit}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-6 bg-card rounded-lg">
                <div className="text-3xl font-bold text-primary mb-2">500+</div>
                <p className="text-sm text-muted-foreground">Career Paths</p>
              </div>
              <div className="text-center p-6 bg-card rounded-lg">
                <div className="text-3xl font-bold text-primary mb-2">95%</div>
                <p className="text-sm text-muted-foreground">Accuracy Rate</p>
              </div>
              <div className="text-center p-6 bg-card rounded-lg">
                <div className="text-3xl font-bold text-primary mb-2">24/7</div>
                <p className="text-sm text-muted-foreground">Availability</p>
              </div>
              <div className="text-center p-6 bg-card rounded-lg">
                <div className="text-3xl font-bold text-primary mb-2">60%</div>
                <p className="text-sm text-muted-foreground">Time Savings</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center bg-gradient-to-r from-primary to-secondary rounded-2xl p-8 lg:p-12 text-white">
          <h2 className="text-3xl lg:text-4xl font-bold mb-4">
            Ready to Transform Career Guidance?
          </h2>
          <p className="text-lg opacity-90 mb-8 max-w-2xl mx-auto">
            Join thousands of students and hundreds of institutions already using our platform 
            to make informed career decisions.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" variant="secondary" asChild>
              <Link to="/register">
                Start Free Trial <ChevronRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" className="bg-white/10 border-white/20 text-white hover:bg-white/20" asChild>
              <Link to="/login">Sign In</Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Features;