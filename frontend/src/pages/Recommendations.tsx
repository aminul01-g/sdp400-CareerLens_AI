import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Target, 
  TrendingUp, 
  DollarSign, 
  GraduationCap, 
  Users, 
  Clock,
  MapPin,
  BookOpen,
  Award,
  Download,
  Heart,
  Share
} from "lucide-react";

// Mock recommendations data
const mockRecommendations = [
  {
    id: 1,
    title: "Software Developer",
    confidence: 92,
    category: "Technology",
    description: "Design, develop, and maintain software applications and systems. Work with programming languages like JavaScript, Python, Java, and modern frameworks to create digital solutions.",
    averageSalary: "$85,000 - $120,000",
    growthRate: "22%",
    jobOutlook: "Much faster than average",
    educationRequired: "Bachelor's degree in Computer Science or related field",
    skills: ["Programming", "Problem Solving", "Teamwork", "Communication", "Logic"],
    workEnvironment: "Office, Remote, Hybrid",
    industries: ["Technology", "Finance", "Healthcare", "E-commerce"],
    careerPath: [
      "Junior Developer",
      "Software Developer",
      "Senior Developer",
      "Tech Lead",
      "Engineering Manager"
    ],
    dailyTasks: [
      "Write and test code",
      "Debug software issues",
      "Collaborate with team members",
      "Review code and documentation",
      "Participate in planning meetings"
    ]
  },
  {
    id: 2,
    title: "Data Scientist",
    confidence: 88,
    category: "Analytics",
    description: "Analyze large datasets to extract insights and patterns that help organizations make data-driven decisions. Use statistical methods, machine learning, and data visualization tools.",
    averageSalary: "$90,000 - $140,000",
    growthRate: "35%",
    jobOutlook: "Much faster than average",
    educationRequired: "Bachelor's in Mathematics, Statistics, or Computer Science",
    skills: ["Statistics", "Python/R", "Machine Learning", "Data Visualization", "SQL"],
    workEnvironment: "Office, Remote",
    industries: ["Technology", "Finance", "Healthcare", "Retail", "Research"],
    careerPath: [
      "Data Analyst",
      "Junior Data Scientist",
      "Data Scientist",
      "Senior Data Scientist",
      "Data Science Manager"
    ],
    dailyTasks: [
      "Clean and analyze data",
      "Build predictive models",
      "Create data visualizations",
      "Present findings to stakeholders",
      "Collaborate with business teams"
    ]
  },
  {
    id: 3,
    title: "UX/UI Designer",
    confidence: 85,
    category: "Design",
    description: "Create user-friendly and visually appealing interfaces for digital products. Conduct user research, design wireframes and prototypes, and ensure optimal user experiences.",
    averageSalary: "$70,000 - $110,000",
    growthRate: "13%",
    jobOutlook: "Faster than average",
    educationRequired: "Bachelor's in Design, HCI, or related field",
    skills: ["Design Thinking", "Prototyping", "User Research", "Figma/Sketch", "HTML/CSS"],
    workEnvironment: "Office, Remote, Studio",
    industries: ["Technology", "Media", "E-commerce", "Consulting"],
    careerPath: [
      "Junior Designer",
      "UX/UI Designer",
      "Senior Designer",
      "Design Lead",
      "Design Director"
    ],
    dailyTasks: [
      "Create wireframes and mockups",
      "Conduct user interviews",
      "Design prototypes",
      "Collaborate with developers",
      "Test and iterate designs"
    ]
  },
  {
    id: 4,
    title: "Product Manager",
    confidence: 82,
    category: "Business",
    description: "Guide product development from conception to launch. Work cross-functionally with engineering, design, and business teams to deliver products that meet user needs and business goals.",
    averageSalary: "$95,000 - $150,000",
    growthRate: "19%",
    jobOutlook: "Faster than average",
    educationRequired: "Bachelor's in Business, Engineering, or related field",
    skills: ["Strategic Thinking", "Communication", "Analytics", "Project Management", "Leadership"],
    workEnvironment: "Office, Remote",
    industries: ["Technology", "Finance", "Healthcare", "Consumer Goods"],
    careerPath: [
      "Associate Product Manager",
      "Product Manager",
      "Senior Product Manager",
      "Principal Product Manager",
      "VP of Product"
    ],
    dailyTasks: [
      "Define product strategy",
      "Gather user requirements",
      "Prioritize features",
      "Coordinate with teams",
      "Analyze product metrics"
    ]
  },
  {
    id: 5,
    title: "Marketing Specialist",
    confidence: 78,
    category: "Marketing",
    description: "Develop and implement marketing strategies to promote products and services. Create campaigns, analyze market trends, and engage with target audiences across various channels.",
    averageSalary: "$45,000 - $75,000",
    growthRate: "10%",
    jobOutlook: "As fast as average",
    educationRequired: "Bachelor's in Marketing, Communications, or Business",
    skills: ["Content Creation", "Analytics", "Social Media", "Communication", "Creativity"],
    workEnvironment: "Office, Remote, Agency",
    industries: ["Marketing", "Technology", "Retail", "Healthcare", "Finance"],
    careerPath: [
      "Marketing Coordinator",
      "Marketing Specialist",
      "Marketing Manager",
      "Senior Marketing Manager",
      "Marketing Director"
    ],
    dailyTasks: [
      "Create marketing content",
      "Manage social media",
      "Analyze campaign performance",
      "Coordinate with sales team",
      "Research market trends"
    ]
  }
];

export default function Recommendations() {
  const [selectedCareer, setSelectedCareer] = useState(mockRecommendations[0]);
  const [savedCareers, setSavedCareers] = useState<number[]>([]);

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

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      "Technology": "bg-primary",
      "Analytics": "bg-secondary", 
      "Design": "bg-accent",
      "Business": "bg-success",
      "Marketing": "bg-warning"
    };
    return colors[category] || "bg-muted";
  };

  const toggleSaveCareer = (careerId: number) => {
    setSavedCareers(prev => 
      prev.includes(careerId) 
        ? prev.filter(id => id !== careerId)
        : [...prev, careerId]
    );
  };

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
            Your Career Recommendations
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Based on your assessment, here are personalized career paths that match your interests, 
            personality, and skills. Each recommendation includes detailed insights to help you make informed decisions.
          </p>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6 text-center">
              <Target className="h-8 w-8 text-primary mx-auto mb-2" />
              <div className="text-2xl font-bold text-foreground">{mockRecommendations.length}</div>
              <p className="text-sm text-muted-foreground">Career Matches</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6 text-center">
              <TrendingUp className="h-8 w-8 text-success mx-auto mb-2" />
              <div className="text-2xl font-bold text-foreground">92%</div>
              <p className="text-sm text-muted-foreground">Top Match Score</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6 text-center">
              <DollarSign className="h-8 w-8 text-accent mx-auto mb-2" />
              <div className="text-2xl font-bold text-foreground">$85K</div>
              <p className="text-sm text-muted-foreground">Avg. Starting Salary</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6 text-center">
              <Users className="h-8 w-8 text-secondary mx-auto mb-2" />
              <div className="text-2xl font-bold text-foreground">22%</div>
              <p className="text-sm text-muted-foreground">Avg. Growth Rate</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Career List */}
          <div className="lg:col-span-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Target className="h-5 w-5 mr-2" />
                  Your Matches
                </CardTitle>
                <CardDescription>
                  Ranked by compatibility with your profile
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="space-y-2">
                  {mockRecommendations.map((career, index) => (
                    <div
                      key={career.id}
                      className={`p-4 cursor-pointer transition-all duration-200 hover:bg-muted/50 border-l-4 ${
                        selectedCareer.id === career.id 
                          ? `${getCategoryColor(career.category)} bg-muted/30` 
                          : "border-transparent"
                      }`}
                      onClick={() => setSelectedCareer(career)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="text-sm font-semibold text-muted-foreground">
                              #{index + 1}
                            </span>
                            <Badge variant="outline" className="text-xs">
                              {career.category}
                            </Badge>
                          </div>
                          <h3 className="font-semibold text-foreground mb-1 truncate">
                            {career.title}
                          </h3>
                          <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                            {career.description}
                          </p>
                          <div className="flex items-center justify-between">
                            <Badge variant={getConfidenceBadgeVariant(career.confidence)}>
                              <span className={getConfidenceColor(career.confidence)}>
                                {career.confidence}% match
                              </span>
                            </Badge>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleSaveCareer(career.id);
                              }}
                            >
                              <Heart 
                                className={`h-4 w-4 ${
                                  savedCareers.includes(career.id) 
                                    ? "fill-current text-red-500" 
                                    : "text-muted-foreground"
                                }`} 
                              />
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Career Details */}
          <div className="lg:col-span-8">
            <Card>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center space-x-2 mb-2">
                      <Badge className={getCategoryColor(selectedCareer.category)}>
                        {selectedCareer.category}
                      </Badge>
                      <Badge variant={getConfidenceBadgeVariant(selectedCareer.confidence)}>
                        <span className={getConfidenceColor(selectedCareer.confidence)}>
                          {selectedCareer.confidence}% match
                        </span>
                      </Badge>
                    </div>
                    <CardTitle className="text-2xl">{selectedCareer.title}</CardTitle>
                    <CardDescription className="mt-2">
                      {selectedCareer.description}
                    </CardDescription>
                  </div>
                  <div className="flex space-x-2">
                    <Button variant="outline" size="sm">
                      <Share className="h-4 w-4 mr-2" />
                      Share
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleSaveCareer(selectedCareer.id)}
                    >
                      <Heart 
                        className={`h-4 w-4 mr-2 ${
                          savedCareers.includes(selectedCareer.id) 
                            ? "fill-current text-red-500" 
                            : ""
                        }`} 
                      />
                      {savedCareers.includes(selectedCareer.id) ? "Saved" : "Save"}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="overview" className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="details">Details</TabsTrigger>
                    <TabsTrigger value="path">Career Path</TabsTrigger>
                    <TabsTrigger value="daily">Daily Life</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="overview" className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <h4 className="font-semibold text-foreground mb-3 flex items-center">
                          <DollarSign className="h-4 w-4 mr-2" />
                          Salary Range
                        </h4>
                        <p className="text-lg font-medium text-success">{selectedCareer.averageSalary}</p>
                        <p className="text-sm text-muted-foreground">National average</p>
                      </div>
                      
                      <div>
                        <h4 className="font-semibold text-foreground mb-3 flex items-center">
                          <TrendingUp className="h-4 w-4 mr-2" />
                          Job Growth
                        </h4>
                        <p className="text-lg font-medium text-success">{selectedCareer.growthRate}</p>
                        <p className="text-sm text-muted-foreground">{selectedCareer.jobOutlook}</p>
                      </div>
                      
                      <div>
                        <h4 className="font-semibold text-foreground mb-3 flex items-center">
                          <GraduationCap className="h-4 w-4 mr-2" />
                          Education Required
                        </h4>
                        <p className="text-sm text-foreground">{selectedCareer.educationRequired}</p>
                      </div>
                      
                      <div>
                        <h4 className="font-semibold text-foreground mb-3 flex items-center">
                          <MapPin className="h-4 w-4 mr-2" />
                          Work Environment
                        </h4>
                        <p className="text-sm text-foreground">{selectedCareer.workEnvironment}</p>
                      </div>
                    </div>

                    <div>
                      <h4 className="font-semibold text-foreground mb-3 flex items-center">
                        <Award className="h-4 w-4 mr-2" />
                        Key Skills
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedCareer.skills.map((skill) => (
                          <Badge key={skill} variant="secondary">
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="details" className="space-y-6">
                    <div>
                      <h4 className="font-semibold text-foreground mb-3">Industries</h4>
                      <div className="grid grid-cols-2 gap-2">
                        {selectedCareer.industries.map((industry) => (
                          <div key={industry} className="p-3 border rounded-lg">
                            <p className="text-sm font-medium">{industry}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="font-semibold text-foreground mb-3">Match Analysis</h4>
                      <div className="space-y-3">
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm">Interests Alignment</span>
                            <span className="text-sm font-medium">95%</span>
                          </div>
                          <Progress value={95} className="h-2" />
                        </div>
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm">Skills Match</span>
                            <span className="text-sm font-medium">88%</span>
                          </div>
                          <Progress value={88} className="h-2" />
                        </div>
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm">Personality Fit</span>
                            <span className="text-sm font-medium">92%</span>
                          </div>
                          <Progress value={92} className="h-2" />
                        </div>
                      </div>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="path" className="space-y-6">
                    <div>
                      <h4 className="font-semibold text-foreground mb-3">Typical Career Progression</h4>
                      <div className="space-y-4">
                        {selectedCareer.careerPath.map((role, index) => (
                          <div key={index} className="flex items-center space-x-4">
                            <div className="flex-shrink-0 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm font-medium">
                              {index + 1}
                            </div>
                            <div className="flex-1">
                              <p className="font-medium text-foreground">{role}</p>
                              <p className="text-sm text-muted-foreground">
                                {index === 0 && "Entry level position"}
                                {index === 1 && "2-4 years experience"}
                                {index === 2 && "5-8 years experience"}
                                {index === 3 && "8-12 years experience"}
                                {index === 4 && "12+ years experience"}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="daily" className="space-y-6">
                    <div>
                      <h4 className="font-semibold text-foreground mb-3 flex items-center">
                        <Clock className="h-4 w-4 mr-2" />
                        Typical Daily Tasks
                      </h4>
                      <div className="space-y-3">
                        {selectedCareer.dailyTasks.map((task, index) => (
                          <div key={index} className="flex items-start space-x-3 p-3 border rounded-lg">
                            <div className="w-2 h-2 bg-primary rounded-full mt-2"></div>
                            <p className="text-sm text-foreground">{task}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
          <Button variant="hero" size="lg" asChild>
            <Link to="/report">
              <Download className="h-5 w-5 mr-2" />
              Download Full Report
            </Link>
          </Button>
          <Button variant="outline" size="lg" asChild>
            <Link to="/quiz">
              <BookOpen className="h-5 w-5 mr-2" />
              Retake Assessment
            </Link>
          </Button>
          <Button variant="secondary" size="lg" asChild>
            <Link to="/feedback">
              <Users className="h-5 w-5 mr-2" />
              Share Feedback
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}