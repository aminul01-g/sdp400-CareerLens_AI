import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Target, 
  Eye, 
  Users, 
  GraduationCap, 
  Lightbulb, 
  Award,
  Building2,
  Globe
} from "lucide-react";

const About = () => {
  const teamMembers = [
    {
      name: "Dr. Sarah Chen",
      role: "AI Research Lead",
      expertise: "Machine Learning & Career Psychology"
    },
    {
      name: "Michael Rodriguez",
      role: "Frontend Developer",
      expertise: "React & User Experience Design"
    },
    {
      name: "Prof. James Wilson",
      role: "Educational Consultant",
      expertise: "Career Counseling & Student Development"
    },
    {
      name: "Lisa Thompson",
      role: "Data Scientist",
      expertise: "Predictive Analytics & Career Trends"
    }
  ];

  const values = [
    {
      icon: Target,
      title: "Precision",
      description: "We use advanced AI algorithms to provide accurate and personalized career recommendations based on comprehensive student data analysis."
    },
    {
      icon: Users,
      title: "Accessibility",
      description: "Making quality career guidance accessible to all students, regardless of their background or educational institution."
    },
    {
      icon: Lightbulb,
      title: "Innovation",
      description: "Continuously improving our AI models and user experience to stay at the forefront of educational technology."
    },
    {
      icon: Award,
      title: "Excellence",
      description: "Committed to delivering the highest quality career guidance through rigorous research and user-centered design."
    }
  ];

  const institutions = [
    "Stanford University",
    "MIT",
    "Harvard University",
    "UC Berkeley",
    "Carnegie Mellon",
    "Georgia Tech"
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      {/* Hero Section */}
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16">
        <div className="text-center max-w-4xl mx-auto">
          <Badge variant="outline" className="mb-6 px-4 py-2">
            <Building2 className="w-4 h-4 mr-2" />
            About CareerGuide AI
          </Badge>
          <h1 className="text-4xl lg:text-6xl font-bold mb-6">
            Empowering Students Through{" "}
            <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              AI-Driven Career Guidance
            </span>
          </h1>
          <p className="text-xl text-muted-foreground leading-relaxed mb-8">
            We're revolutionizing how students discover their career paths by combining cutting-edge 
            artificial intelligence with proven career counseling methodologies.
          </p>
        </div>
      </section>

      {/* Mission & Vision */}
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid md:grid-cols-2 gap-8 max-w-6xl mx-auto">
          <Card className="p-8 bg-card/50 backdrop-blur-sm border-primary/20">
            <div className="flex items-center mb-6">
              <div className="p-3 bg-primary/10 rounded-lg mr-4">
                <Target className="w-8 h-8 text-primary" />
              </div>
              <h2 className="text-2xl font-bold">Our Mission</h2>
            </div>
            <p className="text-muted-foreground leading-relaxed">
              To democratize access to personalized career guidance by leveraging artificial intelligence 
              to analyze student profiles and provide data-driven recommendations that help students make 
              informed decisions about their future careers.
            </p>
          </Card>

          <Card className="p-8 bg-card/50 backdrop-blur-sm border-secondary/20">
            <div className="flex items-center mb-6">
              <div className="p-3 bg-secondary/10 rounded-lg mr-4">
                <Eye className="w-8 h-8 text-secondary" />
              </div>
              <h2 className="text-2xl font-bold">Our Vision</h2>
            </div>
            <p className="text-muted-foreground leading-relaxed">
              A world where every student has access to intelligent, personalized career guidance that 
              helps them discover their true potential and pursue fulfilling careers aligned with their 
              interests, skills, and aspirations.
            </p>
          </Card>
        </div>
      </section>

      {/* Core Values */}
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl lg:text-4xl font-bold mb-4">Our Core Values</h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            The principles that guide our work and drive our commitment to student success.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
          {values.map((value, index) => (
            <Card key={index} className="p-6 text-center hover:shadow-lg transition-all duration-300 bg-card/50 backdrop-blur-sm">
              <div className="p-3 bg-gradient-to-r from-primary/10 to-secondary/10 rounded-lg w-fit mx-auto mb-4">
                <value.icon className="w-8 h-8 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-3">{value.title}</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">{value.description}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* Team Section */}
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl lg:text-4xl font-bold mb-4">Meet Our Team</h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            A diverse group of experts passionate about education, technology, and student success.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
          {teamMembers.map((member, index) => (
            <Card key={index} className="p-6 text-center hover:shadow-lg transition-all duration-300">
              <div className="w-20 h-20 bg-gradient-to-r from-primary to-secondary rounded-full flex items-center justify-center mx-auto mb-4">
                <GraduationCap className="w-10 h-10 text-white" />
              </div>
              <h3 className="text-lg font-semibold mb-2">{member.name}</h3>
              <p className="text-primary font-medium text-sm mb-2">{member.role}</p>
              <p className="text-muted-foreground text-xs">{member.expertise}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* Educational Impact */}
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="bg-gradient-to-r from-primary/5 to-secondary/5 rounded-2xl p-8 lg:p-12">
          <div className="text-center mb-12">
            <h2 className="text-3xl lg:text-4xl font-bold mb-4">
              Impact on Educational Institutions
            </h2>
            <p className="text-muted-foreground text-lg max-w-3xl mx-auto">
              Our platform provides immense value to schools, colleges, and universities by enhancing 
              their career counseling capabilities and improving student outcomes.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 mb-12">
            <div className="text-center">
              <div className="text-4xl font-bold text-primary mb-2">85%</div>
              <p className="text-muted-foreground">Improved student satisfaction with career guidance</p>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-primary mb-2">60%</div>
              <p className="text-muted-foreground">Reduction in career counselor workload</p>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-primary mb-2">92%</div>
              <p className="text-muted-foreground">Student engagement with career planning</p>
            </div>
          </div>

          <Card className="p-6">
            <CardContent className="p-0">
              <h3 className="text-xl font-semibold mb-4 flex items-center">
                <Globe className="w-5 h-5 mr-2 text-primary" />
                Trusted by Leading Institutions
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {institutions.map((institution, index) => (
                  <div key={index} className="text-muted-foreground text-sm text-center p-2 bg-background rounded">
                    {institution}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
};

export default About;