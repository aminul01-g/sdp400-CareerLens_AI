import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { 
  Brain, 
  Target, 
  Download, 
  MessageSquare, 
  Clock, 
  CheckCircle,
  ArrowRight,
  TrendingUp,
  BookOpen,
  Users,
  Star
} from "lucide-react";

// Mock data - in a real app, this would come from an API
const mockUser = {
  name: "John Doe",
  email: "john.doe@example.com",
  educationLevel: "Undergraduate",
  joinedDate: "2024-01-15"
};

const mockQuizStatus = {
  completed: false,
  progress: 65,
  totalQuestions: 50,
  answeredQuestions: 32,
  estimatedTimeRemaining: 15 // minutes
};

const mockRecommendations = [
  {
    id: 1,
    title: "Software Developer",
    confidence: 92,
    description: "Build applications and software solutions using programming languages like JavaScript, Python, and Java.",
    averageSalary: "$85,000 - $120,000",
    growthRate: "22%",
    skills: ["Programming", "Problem Solving", "Teamwork"],
    education: "Bachelor's in Computer Science"
  },
  {
    id: 2,
    title: "Data Scientist",
    confidence: 88,
    description: "Analyze complex data to help organizations make informed business decisions using statistical methods and machine learning.",
    averageSalary: "$90,000 - $140,000",
    growthRate: "35%",
    skills: ["Statistics", "Python/R", "Machine Learning"],
    education: "Bachelor's in Mathematics/Statistics"
  },
  {
    id: 3,
    title: "UX/UI Designer",
    confidence: 85,
    description: "Design user-friendly interfaces and experiences for digital products, combining creativity with user research.",
    averageSalary: "$70,000 - $110,000",
    growthRate: "13%",
    skills: ["Design Thinking", "Prototyping", "User Research"],
    education: "Bachelor's in Design or related field"
  }
];

const mockStats = {
  totalUsers: "12,847",
  averageCompletion: "18 minutes",
  successRate: "94%",
  careerPaths: "500+"
};

export default function Dashboard() {
  const [isLoading, setIsLoading] = useState(true);
  const [currentUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch(e) { return null; }
  });

  useEffect(() => {
    // Simulate loading
    const timer = setTimeout(() => setIsLoading(false), 1000);
    return () => clearTimeout(timer);
  }, []);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return "text-success";
    if (confidence >= 80) return "text-accent";
    if (confidence >= 70) return "text-warning";
    return "text-muted-foreground";
  };

  const getConfidenceBadgeVariant = (confidence: number) => {
    if (confidence >= 90) return "default";
    if (confidence >= 80) return "secondary";
    return "outline";
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground mb-2">
                Welcome back, {currentUser?.name || mockUser.name}! 👋
              </h1>
              <p className="text-muted-foreground">
                Continue your career discovery journey and explore new opportunities.
              </p>
            </div>
            <div className="mt-4 md:mt-0">
              <Badge variant="outline" className="text-sm">
                {(currentUser?.education_level || currentUser?.educationLevel) || mockUser.educationLevel} Student
              </Badge>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6 text-center">
              <Users className="h-8 w-8 text-primary mx-auto mb-2" />
              <div className="text-2xl font-bold text-foreground">{mockStats.totalUsers}</div>
              <p className="text-sm text-muted-foreground">Students Guided</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6 text-center">
              <Clock className="h-8 w-8 text-accent mx-auto mb-2" />
              <div className="text-2xl font-bold text-foreground">{mockStats.averageCompletion}</div>
              <p className="text-sm text-muted-foreground">Avg. Completion</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6 text-center">
              <TrendingUp className="h-8 w-8 text-success mx-auto mb-2" />
              <div className="text-2xl font-bold text-foreground">{mockStats.successRate}</div>
              <p className="text-sm text-muted-foreground">Success Rate</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6 text-center">
              <Target className="h-8 w-8 text-secondary mx-auto mb-2" />
              <div className="text-2xl font-bold text-foreground">{mockStats.careerPaths}</div>
              <p className="text-sm text-muted-foreground">Career Paths</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Assessment Status */}
          <Card className="h-fit">
            <CardHeader>
              <div className="flex items-center space-x-2">
                <Brain className="h-5 w-5 text-primary" />
                <CardTitle>Career Assessment</CardTitle>
              </div>
              <CardDescription>
                Complete your assessment to get personalized career recommendations
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {mockQuizStatus.completed ? (
                <div className="text-center py-6">
                  <CheckCircle className="h-12 w-12 text-success mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    Assessment Completed!
                  </h3>
                  <p className="text-muted-foreground mb-4">
                    Great job! You've completed your career assessment.
                  </p>
                  <Button variant="outline" asChild>
                    <Link to="/quiz">
                      Retake Assessment
                    </Link>
                  </Button>
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">
                        {mockQuizStatus.answeredQuestions} of {mockQuizStatus.totalQuestions} questions
                      </span>
                      <span className="font-medium text-foreground">
                        {mockQuizStatus.progress}%
                      </span>
                    </div>
                    <Progress value={mockQuizStatus.progress} className="h-2" />
                  </div>
                  
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <div className="flex items-center">
                      <Clock className="h-4 w-4 mr-2" />
                      ~{mockQuizStatus.estimatedTimeRemaining} min remaining
                    </div>
                  </div>

                  <Button className="w-full" variant="hero" asChild>
                    <Link to="/quiz">
                      {mockQuizStatus.progress > 0 ? "Continue Assessment" : "Start Assessment"}
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          {/* Top Career Recommendations */}
          <Card className="h-fit">
            <CardHeader>
              <div className="flex items-center space-x-2">
                <Target className="h-5 w-5 text-primary" />
                <CardTitle>Your Top Career Matches</CardTitle>
              </div>
              <CardDescription>
                {mockQuizStatus.completed 
                  ? "Based on your completed assessment"
                  : "Preview recommendations (complete assessment for full results)"
                }
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockRecommendations.slice(0, 3).map((career, index) => (
                  <div
                    key={career.id}
                    className={`p-4 rounded-lg border transition-all duration-200 hover:shadow-md ${
                      !mockQuizStatus.completed ? "opacity-60" : ""
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <span className="text-lg font-semibold text-foreground">
                          #{index + 1}
                        </span>
                        <h3 className="font-semibold text-foreground">{career.title}</h3>
                      </div>
                      <Badge variant={getConfidenceBadgeVariant(career.confidence)}>
                        <span className={getConfidenceColor(career.confidence)}>
                          {career.confidence}% match
                        </span>
                      </Badge>
                    </div>
                    
                    <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                      {career.description}
                    </p>
                    
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{career.averageSalary}</span>
                      <span className="flex items-center">
                        <TrendingUp className="h-3 w-3 mr-1" />
                        {career.growthRate} growth
                      </span>
                    </div>
                  </div>
                ))}
                
                <Button variant="outline" className="w-full" asChild>
                  <Link to="/recommendations">
                    View All Recommendations
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Action Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          {/* Download Report */}
          <Card className="hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
            <CardContent className="p-6 text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-gradient-to-r from-primary to-secondary rounded-lg mb-4">
                <Download className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">
                Download Report
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Get a comprehensive PDF report of your career assessment and recommendations.
              </p>
              <Button 
                variant="outline" 
                className="w-full" 
                disabled={!mockQuizStatus.completed}
                asChild
              >
                <Link to="/report">
                  Download PDF
                </Link>
              </Button>
            </CardContent>
          </Card>

          {/* Explore Careers */}
          <Card className="hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
            <CardContent className="p-6 text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-gradient-to-r from-accent to-secondary rounded-lg mb-4">
                <BookOpen className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">
                Explore Careers
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Browse our comprehensive database of career paths and explore new possibilities.
              </p>
              <Button variant="outline" className="w-full" asChild>
                <Link to="/careers">
                  Browse Careers
                </Link>
              </Button>
            </CardContent>
          </Card>

          {/* Give Feedback */}
          <Card className="hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
            <CardContent className="p-6 text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-gradient-to-r from-success to-accent rounded-lg mb-4">
                <MessageSquare className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">
                Share Feedback
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Help us improve by sharing your experience and suggestions.
              </p>
              <Button variant="outline" className="w-full" asChild>
                <Link to="/feedback">
                  Give Feedback
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity or Tips */}
        <Card className="mt-8">
          <CardHeader>
            <div className="flex items-center space-x-2">
              <Star className="h-5 w-5 text-primary" />
              <CardTitle>Career Development Tips</CardTitle>
            </div>
            <CardDescription>
              Actionable advice to help you advance in your chosen career path
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-primary rounded-full mt-2"></div>
                  <div>
                    <h4 className="font-medium text-foreground">Build a Strong Portfolio</h4>
                    <p className="text-sm text-muted-foreground">
                      Showcase your best work and projects to potential employers.
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-secondary rounded-full mt-2"></div>
                  <div>
                    <h4 className="font-medium text-foreground">Network Actively</h4>
                    <p className="text-sm text-muted-foreground">
                      Connect with professionals in your field through LinkedIn and industry events.
                    </p>
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-accent rounded-full mt-2"></div>
                  <div>
                    <h4 className="font-medium text-foreground">Continuous Learning</h4>
                    <p className="text-sm text-muted-foreground">
                      Stay updated with industry trends and develop new skills regularly.
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-success rounded-full mt-2"></div>
                  <div>
                    <h4 className="font-medium text-foreground">Gain Experience</h4>
                    <p className="text-sm text-muted-foreground">
                      Look for internships, volunteer work, or part-time opportunities in your field.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}