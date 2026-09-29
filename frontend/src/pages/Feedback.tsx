import { useState } from "react";
import api from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/hooks/use-toast";
import { 
  MessageSquare, 
  Star, 
  Send, 
  CheckCircle, 
  AlertCircle,
  Lightbulb,
  Bug,
  Heart
} from "lucide-react";

const Feedback = () => {
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    feedbackType: "",
    rating: "",
    subject: "",
    message: "",
    features: [] as string[],
    allowContact: false
  });

  const feedbackTypes = [
    { value: "suggestion", label: "Feature Suggestion", icon: Lightbulb, color: "text-blue-500" },
    { value: "bug", label: "Bug Report", icon: Bug, color: "text-red-500" },
    { value: "general", label: "General Feedback", icon: MessageSquare, color: "text-green-500" },
    { value: "appreciation", label: "Appreciation", icon: Heart, color: "text-pink-500" }
  ];

  const platformFeatures = [
    "Career Assessment Quiz",
    "AI Recommendations",
    "Career Reports",
    "User Dashboard",
    "Mobile Experience",
    "Overall Design"
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payload = {
        name: formData.name,
        email: formData.email,
        feedbackType: formData.feedbackType,
        rating: formData.rating,
        subject: formData.subject,
        message: formData.message,
        features: formData.features,
        allowContact: formData.allowContact
      };

      // include token if user logged in
      const token = localStorage.getItem('token') || undefined;
      await api.submitFeedback(payload, token);

      toast({
        title: "Feedback Submitted Successfully!",
        description: "Thank you for helping us improve CareerGuide AI. We'll review your feedback and get back to you soon.",
        duration: 5000,
      });

      setFormData({
        name: "",
        email: "",
        feedbackType: "",
        rating: "",
        subject: "",
        message: "",
        features: [],
        allowContact: false
      });
    } catch (err) {
      console.error('Submit feedback error', err);
      toast({
        title: "Failed to submit feedback",
        description: (err as any)?.message || 'Please try again later.',
        variant: 'destructive'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFeatureToggle = (feature: string) => {
    setFormData(prev => ({
      ...prev,
      features: prev.features.includes(feature)
        ? prev.features.filter(f => f !== feature)
        : [...prev.features, feature]
    }));
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <Badge variant="outline" className="mb-4 px-4 py-2">
            <MessageSquare className="w-4 h-4 mr-2" />
            Your Feedback Matters
          </Badge>
          <h1 className="text-4xl lg:text-5xl font-bold mb-4">
            Help Us{" "}
            <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              Improve
            </span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Your insights and suggestions help us create a better career guidance experience for all students.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Main Feedback Form */}
            <div className="lg:col-span-2 space-y-6">
              {/* Personal Information */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <CheckCircle className="w-5 h-5 mr-2 text-primary" />
                    Contact Information
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="name">Name</Label>
                      <Input
                        id="name"
                        value={formData.name}
                        onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="Your full name"
                        required
                      />
                    </div>
                    <div>
                      <Label htmlFor="email">Email</Label>
                      <Input
                        id="email"
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                        placeholder="your.email@example.com"
                        required
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Feedback Type */}
              <Card>
                <CardHeader>
                  <CardTitle>Type of Feedback</CardTitle>
                </CardHeader>
                <CardContent>
                  <RadioGroup
                    value={formData.feedbackType}
                    onValueChange={(value) => setFormData(prev => ({ ...prev, feedbackType: value }))}
                    className="grid md:grid-cols-2 gap-4"
                  >
                    {feedbackTypes.map((type) => (
                      <div key={type.value} className="flex items-center space-x-2 p-3 border rounded-lg hover:bg-muted/50 transition-colors">
                        <RadioGroupItem value={type.value} id={type.value} />
                        <Label htmlFor={type.value} className="flex items-center flex-1 cursor-pointer">
                          <type.icon className={`w-4 h-4 mr-2 ${type.color}`} />
                          {type.label}
                        </Label>
                      </div>
                    ))}
                  </RadioGroup>
                </CardContent>
              </Card>

              {/* Overall Rating */}
              <Card>
                <CardHeader>
                  <CardTitle>Overall Experience Rating</CardTitle>
                </CardHeader>
                <CardContent>
                  <RadioGroup
                    value={formData.rating}
                    onValueChange={(value) => setFormData(prev => ({ ...prev, rating: value }))}
                    className="flex flex-wrap gap-4"
                  >
                    {[1, 2, 3, 4, 5].map((rating) => (
                      <div key={rating} className="flex items-center space-x-2">
                        <RadioGroupItem value={rating.toString()} id={`rating-${rating}`} />
                        <Label htmlFor={`rating-${rating}`} className="flex items-center cursor-pointer">
                          <div className="flex">
                            {[...Array(5)].map((_, i) => (
                              <Star
                                key={i}
                                className={`w-4 h-4 ${
                                  i < rating ? 'text-yellow-400 fill-current' : 'text-muted-foreground'
                                }`}
                              />
                            ))}
                          </div>
                          <span className="ml-2 text-sm">{rating} Star{rating > 1 ? 's' : ''}</span>
                        </Label>
                      </div>
                    ))}
                  </RadioGroup>
                </CardContent>
              </Card>

              {/* Detailed Feedback */}
              <Card>
                <CardHeader>
                  <CardTitle>Your Feedback</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label htmlFor="subject">Subject</Label>
                    <Input
                      id="subject"
                      value={formData.subject}
                      onChange={(e) => setFormData(prev => ({ ...prev, subject: e.target.value }))}
                      placeholder="Brief summary of your feedback"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="message">Detailed Message</Label>
                    <Textarea
                      id="message"
                      value={formData.message}
                      onChange={(e) => setFormData(prev => ({ ...prev, message: e.target.value }))}
                      placeholder="Please share your thoughts, suggestions, or describe any issues you've encountered..."
                      className="min-h-32"
                      required
                    />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Feature Feedback */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Which features would you like to comment on?</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {platformFeatures.map((feature) => (
                      <div key={feature} className="flex items-center space-x-2">
                        <Checkbox
                          id={feature}
                          checked={formData.features.includes(feature)}
                          onCheckedChange={() => handleFeatureToggle(feature)}
                        />
                        <Label htmlFor={feature} className="text-sm cursor-pointer">
                          {feature}
                        </Label>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Contact Preference */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Follow-up</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="allowContact"
                      checked={formData.allowContact}
                      onCheckedChange={(checked) => 
                        setFormData(prev => ({ ...prev, allowContact: checked as boolean }))
                      }
                    />
                    <Label htmlFor="allowContact" className="text-sm cursor-pointer">
                      Allow us to contact you about your feedback
                    </Label>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    We'll only contact you if we need clarification or have updates related to your feedback.
                  </p>
                </CardContent>
              </Card>

              {/* Quick Stats */}
              <Card className="bg-gradient-to-br from-primary/5 to-secondary/5">
                <CardHeader>
                  <CardTitle className="text-lg">Community Impact</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Feedback received</span>
                    <Badge variant="secondary">2,847</Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Features improved</span>
                    <Badge variant="secondary">156</Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Bugs fixed</span>
                    <Badge variant="secondary">89</Badge>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex justify-center pt-6">
            <Button
              type="submit"
              size="lg"
              disabled={isSubmitting || !formData.name || !formData.email || !formData.message}
              className="min-w-48"
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Submitting...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Submit Feedback
                </>
              )}
            </Button>
          </div>
        </form>

        {/* Thank You Message */}
        <div className="mt-12 text-center p-6 bg-gradient-to-r from-primary/10 to-secondary/10 rounded-lg">
          <h3 className="text-lg font-semibold mb-2">Thank You for Your Feedback!</h3>
          <p className="text-muted-foreground">
            Every piece of feedback helps us create a better experience for students worldwide. 
            Your input is invaluable in shaping the future of AI-powered career guidance.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Feedback;