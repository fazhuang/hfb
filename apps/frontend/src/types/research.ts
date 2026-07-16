/** Shared research types used across research components and pages. */

export interface ProjectSummary {
  id: string;
  title: string;
  description: string | null;
  created_at: string | null;
  updated_at: string | null;
}
