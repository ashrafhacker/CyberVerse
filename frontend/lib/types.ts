export type UserRole =
  | 'guest'
  | 'student'
  | 'premium_student'
  | 'instructor'
  | 'moderator'
  | 'administrator'
  | 'developer'
  | 'super_admin';

export type UserStatus = 'pending' | 'active' | 'suspended' | 'banned';

export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  role: UserRole;
  status: UserStatus;
  is_verified: boolean;
  is_2fa_enabled: boolean;
  provider: string;
  created_at: string;
  updated_at: string;
}

export interface Profile {
  user_id: string;
  username: string;
  bio?: string | null;
  banner_url?: string | null;
  avatar_url?: string | null;
  xp: number;
  coins: number;
  level: number;
  rank?: string | null;
  titles: string[];
  badges: string[];
  equipped_title?: string | null;
  equipped_badge?: string | null;
  statistics: Record<string, unknown>;
  settings: Record<string, unknown>;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface APIResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
  error?: string;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  size: number;
  items: T[];
}

export interface Lesson {
  id: string;
  module_id: string;
  title: string;
  description?: string | null;
  order: number;
  content: Record<string, unknown>;
  xp_reward: number;
  coins_reward: number;
  duration_minutes?: number | null;
  is_required: boolean;
}

export interface Quiz {
  id: string;
  lesson_id: string;
  title: string;
  description?: string | null;
  passing_score: number;
  time_limit_minutes?: number | null;
  max_attempts?: number | null;
}

export interface Mission {
  id: string;
  slug: string;
  name: string;
  short_description: string;
  mission_type: string;
  difficulty: string;
  estimated_minutes: number;
  xp_reward: number;
  coins_reward: number;
  is_premium: boolean;
  tags: string[];
  thumbnail_url?: string | null;
}

export interface DailyChallenge {
  id: string;
  title: string;
  description: string;
  task_type: string;
  task_requirement: number;
  xp_reward: number;
  coins_reward: number;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  username: string;
  full_name: string;
  avatar_url?: string | null;
  score: number;
  time_spent_seconds: number;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  content: string;
  is_read: boolean;
  created_at: string;
}

export interface LearningPath {
  id: string;
  slug: string;
  name: string;
  description: string;
  difficulty: string;
  estimated_hours: number;
  is_premium: boolean;
  order: number;
}

export interface Course {
  id: string;
  slug: string;
  name: string;
  description: string;
  short_description: string;
  difficulty: string;
  estimated_hours: number;
  thumbnail_url?: string | null;
  is_premium: boolean;
  tags: string[];
}

export interface PlayerProgress {
  total_xp: number;
  total_coins: number;
  level: number;
  lessons_completed: number;
  missions_completed: number;
  quizzes_passed: number;
  labs_completed: number;
  learning_streak: number;
  longest_streak: number;
  time_spent_seconds: number;
}

export interface LabFacility {
  id: string;
  slug: string;
  name: string;
  description: string;
  facility_type: string;
  min_level: number;
  ue5_map_name?: string | null;
  unlocked: boolean;
}

export interface LabMission {
  id: string;
  facility_id: string;
  slug: string;
  title: string;
  mission_type: string;
  difficulty: string;
  estimated_minutes: number;
  story_context: string;
  objectives: Array<Record<string, unknown>>;
  tools: Array<Record<string, unknown>>;
}

export interface LabSession {
  id: string;
  status: string;
  mode: string;
  mentor_level: string;
  current_facility_slug: string;
  score?: number | null;
  xp_awarded: number;
  coins_awarded: number;
  started_at: string;
  completed_at?: string | null;
}

export interface LabWorld {
  session_id: string;
  scenario_seed: string;
  facility: string;
  company: Record<string, unknown>;
  topology: Record<string, unknown>;
  assets: Array<Record<string, unknown>>;
  identities: Array<Record<string, unknown>>;
  alerts: Array<Record<string, unknown>>;
  evidence: Array<Record<string, unknown>>;
  objectives: Array<Record<string, unknown>>;
  tool_manifest: Array<Record<string, unknown>>;
  safety_metadata: Record<string, unknown>;
}
