/**
 * Zod mirrors of the Pydantic request models.
 *
 * These exist so the client can bind errors to a field *before* a round trip. They
 * deliberately duplicate the server rules rather than trying to fetch them: the
 * server remains the authority (every mutation surfaces its own 422 field errors
 * through `ApiError.fieldErrors`), and a client that trusts its own copy more than
 * the server's is how validation drift starts.
 *
 * The password policy is identical to `app/schemas/auth.py`:
 * >= 8 characters with at least one uppercase, one lowercase, and one digit.
 */
import { z } from "zod";

export const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters long.")
  .max(128, "Password must not exceed 128 characters.")
  .regex(/[a-z]/, "Password must contain a lowercase letter.")
  .regex(/[A-Z]/, "Password must contain an uppercase letter.")
  .regex(/\d/, "Password must contain a digit.");

export const emailSchema = z
  .string()
  .min(1, "Email is required.")
  .email("Enter a valid email address.");

export const nameSchema = z
  .string()
  .min(1, "Name is required.")
  .max(120, "Name must not exceed 120 characters.");

export const loginSchema = z.object({
  email: emailSchema,
  // Login only checks presence: the strength policy belongs to registration, and
  // enforcing it here would tell an attacker the password shape before auth.
  password: z.string().min(1, "Password is required."),
});
export type LoginInput = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    name: nameSchema,
    email: emailSchema,
    password: passwordSchema,
    confirmPassword: z.string().min(1, "Please confirm your password."),
    educationLevel: z.string().max(80).optional(),
    acceptTerms: z.literal(true, {
      errorMap: () => ({ message: "You must accept the terms to continue." }),
    }),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "Passwords do not match.",
    path: ["confirmPassword"],
  });
export type RegisterInput = z.infer<typeof registerSchema>;

const optionalUrl = z
  .string()
  .trim()
  .max(400)
  .refine(
    (value) => value === "" || /^https?:\/\/.+/i.test(value),
    "Enter a full URL starting with http:// or https://",
  )
  .optional()
  .or(z.literal("").transform(() => null))
  .nullable();

export const profileSchema = z.object({
  headline: z.string().trim().max(200, "Headline must be at most 200 characters.").optional(),
  career_goal: z.string().trim().max(2000).optional(),
  bio: z.string().trim().max(4000).optional(),
  location: z.string().trim().max(120).optional(),
  education_level: z.string().trim().max(80).optional(),
  years_experience: z.coerce
    .number({ invalid_type_error: "Enter a number." })
    .min(0, "Experience cannot be negative.")
    .max(60, "Enter a realistic number of years.")
    .optional()
    .or(z.literal("").transform(() => null))
    .nullable(),
  seniority: z
    .enum(["Entry", "Junior", "Mid", "Senior", "Lead", "Principal"])
    .optional()
    .or(z.literal("").transform(() => null))
    .nullable(),
  industry: z.string().trim().max(120, "Industry must be at most 120 characters.").optional(),
  preferred_role_family: z.string().trim().max(80).optional(),
  links: z
    .object({
      github: optionalUrl,
      linkedin: optionalUrl,
      portfolio: optionalUrl,
    })
    .optional(),
});
export type ProfileInput = z.infer<typeof profileSchema>;

export const projectSchema = z
  .object({
    title: z.string().trim().min(1, "Title is required.").max(160, "Title must be at most 160 characters."),
    description: z
      .string()
      .trim()
      .min(1, "Describe what you built.")
      .max(5000, "Description must be at most 5000 characters."),
    tech_stack: z.array(z.string().trim().min(1)).max(30, "At most 30 technologies.").optional(),
    role: z.string().trim().max(120).optional(),
    start_date: z.string().optional(),
    end_date: z.string().optional(),
    repo_url: optionalUrl,
    is_public: z.boolean().optional(),
  })
  .refine(
    (values) => !values.start_date || !values.end_date || values.end_date >= values.start_date,
    { message: "The end date must not be before the start date.", path: ["end_date"] },
  );
export type ProjectInput = z.infer<typeof projectSchema>;

const year = z.coerce
  .number({ invalid_type_error: "Enter a year." })
  .int()
  .min(1950, "Enter a realistic year.")
  .max(2100, "Enter a realistic year.");

export const educationSchema = z
  .object({
    institution: z.string().trim().min(1, "Institution is required.").max(180),
    degree: z.string().trim().min(1, "Degree is required.").max(120),
    field_of_study: z.string().trim().max(120).optional(),
    start_year: year.optional().nullable(),
    end_year: year.optional().nullable(),
    grade: z.string().trim().max(40).optional(),
  })
  .refine((values) => !values.start_year || !values.end_year || values.end_year >= values.start_year, {
    message: "The end year must not be before the start year.",
    path: ["end_year"],
  });
export type EducationInput = z.infer<typeof educationSchema>;

export const certificationSchema = z
  .object({
    name: z.string().trim().min(1, "Name is required.").max(160),
    issuer: z.string().trim().min(1, "Issuer is required.").max(160),
    issued_on: z.string().optional().nullable(),
    expires_on: z.string().optional().nullable(),
    credential_url: optionalUrl,
  })
  .refine((values) => !values.issued_on || !values.expires_on || values.expires_on > values.issued_on, {
    message: "The expiry date must be after the issue date.",
    path: ["expires_on"],
  });
export type CertificationInput = z.infer<typeof certificationSchema>;

export const proficiencySchema = z.coerce
  .number()
  .int("Choose a whole number.")
  .min(1, "Proficiency is from 1 to 5.")
  .max(5, "Proficiency is from 1 to 5.");

export const jobRoleSchema = z.object({
  title: z.string().trim().min(1, "Title is required.").max(140),
  family: z.string().trim().min(1, "Family is required.").max(80),
  seniority: z.string().trim().max(40).optional(),
  description: z
    .string()
    .trim()
    .min(1, "A description is required — this is the text the engine matches against.")
    .max(8000),
  responsibilities: z.array(z.string()).max(30).optional(),
  is_active: z.boolean().optional(),
  skills: z
    .array(
      z.object({
        skill_id: z.number().int().positive(),
        weight: z.coerce.number().min(0.01, "Weight must be greater than 0.").max(1, "Weight cannot exceed 1."),
      }),
    )
    .min(1, "A role needs at least one required skill.")
    .max(40, "At most 40 required skills per role."),
});
export type JobRoleInput = z.infer<typeof jobRoleSchema>;

export const feedbackSchema = z.object({
  category: z.enum(["general", "bug", "feature", "ui", "data", "other"]),
  message: z.string().trim().min(5, "Tell us a little more.").max(4000),
  rating: z.number().int().min(1).max(5).optional(),
});
export type FeedbackInput = z.infer<typeof feedbackSchema>;
