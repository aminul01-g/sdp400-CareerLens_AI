import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  ChevronLeft, 
  ChevronRight, 
  Save, 
  Brain, 
  CheckCircle,
  AlertTriangle
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

// Mock quiz data
const mockQuizData = {
  sections: [
    {
      id: "interests",
      title: "Interests & Passions",
      description: "Help us understand what you're passionate about",
      questions: [
        {
          id: 1,
          text: "Which of these activities do you find most engaging?",
          type: "multiple-choice",
          options: [
            "Solving complex problems and puzzles",
            "Creating visual designs and artwork",
            "Helping and working with people",
            "Analyzing data and trends",
            "Building or fixing things"
          ]
        },
        {
          id: 2,
          text: "What type of work environment appeals to you most?",
          type: "multiple-choice",
          options: [
            "Fast-paced startup environment",
            "Structured corporate setting",
            "Creative studio or agency",
            "Research laboratory",
            "Remote/flexible workspace"
          ]
        }
      ]
    },
    {
      id: "personality",
      title: "Personality Traits",
      description: "Let's explore your personality and work style",
      questions: [
        {
          id: 3,
          text: "How do you prefer to work on projects?",
          type: "multiple-choice",
          options: [
            "Independently with minimal supervision",
            "In small collaborative teams",
            "Leading large groups",
            "Following detailed instructions",
            "With constant feedback and iteration"
          ]
        },
        {
          id: 4,
          text: "When facing a challenge, you typically:",
          type: "multiple-choice",
          options: [
            "Research extensively before taking action",
            "Jump in and learn as you go",
            "Seek advice from others",
            "Break it down into smaller steps",
            "Look for creative alternative solutions"
          ]
        }
      ]
    },
    {
      id: "skills",
      title: "Skills & Abilities",
      description: "Tell us about your current skills and strengths",
      questions: [
        {
          id: 5,
          text: "Which subject area are you strongest in?",
          type: "multiple-choice",
          options: [
            "Mathematics and Logic",
            "Language and Communication",
            "Science and Research",
            "Arts and Creativity",
            "Technology and Programming"
          ]
        },
        {
          id: 6,
          text: "What type of thinking comes most naturally to you?",
          type: "multiple-choice",
          options: [
            "Analytical and logical thinking",
            "Creative and imaginative thinking",
            "Strategic and big-picture thinking",
            "Detail-oriented and systematic thinking",
            "Empathetic and people-focused thinking"
          ]
        }
      ]
    }
  ]
};

export default function Quiz() {
  const [currentSection, setCurrentSection] = useState(0);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const navigate = useNavigate();
  const { toast } = useToast();

  const totalQuestions = mockQuizData.sections.reduce((total, section) => total + section.questions.length, 0);
  const answeredQuestions = Object.keys(answers).length;
  const progress = (answeredQuestions / totalQuestions) * 100;

  const currentSectionData = mockQuizData.sections[currentSection];
  const currentQuestionData = currentSectionData.questions[currentQuestion];
  const questionNumber = mockQuizData.sections
    .slice(0, currentSection)
    .reduce((total, section) => total + section.questions.length, 0) + currentQuestion + 1;

  const handleAnswerChange = (value: string) => {
    setAnswers(prev => ({
      ...prev,
      [currentQuestionData.id]: value
    }));
  };

  const handleNext = () => {
    // Check if current question is answered
    if (!answers[currentQuestionData.id]) {
      toast({
        title: "Answer Required",
        description: "Please select an answer before proceeding.",
        variant: "destructive",
      });
      return;
    }

    // Move to next question
    if (currentQuestion < currentSectionData.questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    } else if (currentSection < mockQuizData.sections.length - 1) {
      setCurrentSection(currentSection + 1);
      setCurrentQuestion(0);
    }
  };

  const handlePrevious = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(currentQuestion - 1);
    } else if (currentSection > 0) {
      setCurrentSection(currentSection - 1);
      setCurrentQuestion(mockQuizData.sections[currentSection - 1].questions.length - 1);
    }
  };

  const handleSave = () => {
    // Save progress logic
    toast({
      title: "Progress Saved",
      description: "Your answers have been saved. You can continue later.",
    });
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    
    try {
      // Simulate API submission
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      toast({
        title: "Assessment Complete!",
        description: "Your career recommendations are ready.",
      });
      
      navigate("/recommendations");
    } catch (error) {
      toast({
        title: "Submission Failed",
        description: "There was an error submitting your assessment. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFirstQuestion = currentSection === 0 && currentQuestion === 0;
  const isLastQuestion = currentSection === mockQuizData.sections.length - 1 && 
                         currentQuestion === currentSectionData.questions.length - 1;

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center px-4 py-2 bg-muted rounded-full text-sm font-medium text-muted-foreground mb-4">
            <Brain className="h-4 w-4 mr-2" />
            Career Assessment Quiz
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">
            Discover Your Perfect Career Path
          </h1>
          <p className="text-lg text-muted-foreground">
            Answer these questions honestly to get personalized career recommendations
          </p>
        </div>

        {/* Progress Bar */}
        <Card className="mb-8">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-semibold text-foreground">
                  Question {questionNumber} of {totalQuestions}
                </h3>
                <p className="text-sm text-muted-foreground">
                  Section: {currentSectionData.title}
                </p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-primary">{Math.round(progress)}%</div>
                <p className="text-sm text-muted-foreground">Complete</p>
              </div>
            </div>
            <Progress value={progress} className="h-2" />
          </CardContent>
        </Card>

        {/* Question Card */}
        <Card className="mb-8">
          <CardHeader>
            <div className="flex items-center justify-between">
              <Badge variant="outline">
                {currentSectionData.title}
              </Badge>
              <Badge variant="secondary">
                {currentQuestion + 1} of {currentSectionData.questions.length}
              </Badge>
            </div>
            <CardTitle className="text-xl md:text-2xl">
              {currentQuestionData.text}
            </CardTitle>
            <CardDescription>
              {currentSectionData.description}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RadioGroup
              value={answers[currentQuestionData.id] || ""}
              onValueChange={handleAnswerChange}
              className="space-y-3"
            >
              {currentQuestionData.options.map((option, index) => (
                <div key={index} className="flex items-center space-x-3 p-3 rounded-lg border hover:bg-muted/50 transition-colors">
                  <RadioGroupItem value={option} id={`option-${index}`} />
                  <Label htmlFor={`option-${index}`} className="flex-1 cursor-pointer">
                    {option}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </CardContent>
        </Card>

        {/* Navigation */}
        <div className="flex flex-col sm:flex-row gap-4 justify-between items-center">
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handlePrevious}
              disabled={isFirstQuestion}
              className="flex items-center"
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              Previous
            </Button>
            
            <Button
              variant="secondary"
              onClick={handleSave}
              className="flex items-center"
            >
              <Save className="h-4 w-4 mr-2" />
              Save Progress
            </Button>
          </div>

          <div className="flex gap-2">
            {isLastQuestion ? (
              <Button
                variant="hero"
                onClick={handleSubmit}
                disabled={!answers[currentQuestionData.id] || isSubmitting}
                className="flex items-center"
              >
                {isSubmitting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Submitting...
                  </>
                ) : (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Complete Assessment
                  </>
                )}
              </Button>
            ) : (
              <Button
                variant="default"
                onClick={handleNext}
                disabled={!answers[currentQuestionData.id]}
                className="flex items-center"
              >
                Next
                <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            )}
          </div>
        </div>

        {/* Help Section */}
        <Alert className="mt-8">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <strong>Tip:</strong> Answer honestly for the most accurate career recommendations. 
            There are no right or wrong answers - we're looking to understand your unique profile.
          </AlertDescription>
        </Alert>

        {/* Section Progress */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          {mockQuizData.sections.map((section, index) => {
            const sectionQuestions = section.questions.map(q => q.id);
            const sectionAnswered = sectionQuestions.filter(id => answers[id]).length;
            const sectionProgress = (sectionAnswered / sectionQuestions.length) * 100;
            
            return (
              <Card key={section.id} className={`p-4 ${index === currentSection ? 'ring-2 ring-primary' : ''}`}>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-sm">{section.title}</h4>
                  <Badge variant={sectionProgress === 100 ? "default" : "outline"}>
                    {sectionAnswered}/{sectionQuestions.length}
                  </Badge>
                </div>
                <Progress value={sectionProgress} className="h-1" />
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}