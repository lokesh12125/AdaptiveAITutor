import { useQuery } from "@tanstack/react-query";
import { UserRound } from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { Profile } from "@/api/types";
import { ProfileView } from "@/components/ProfileView";
import { ErrorState, PageLoading } from "@/components/ui";

const GOAL: Record<string, string> = { basics: "Learning programming from the start", course: "Keeping up with a course", dsa: "Practising data structures and algorithms", explore: "Exploring" };
const EXPERIENCE: Record<string, string> = { new: "New to programming", some: "Knows some basics", intermediate: "Comfortable with Python", advanced: "Experienced" };

export function ProfilePage() {
  const query = useQuery<Profile>({ queryKey: ["profile"], queryFn: () => api<Profile>("/me/profile") });
  if (query.isLoading) return <PageLoading />;
  if (query.isError || !query.data) return <ErrorState error={query.error} what="Your profile" onRetry={() => void query.refetch()} />;
  const { user } = query.data;
  return (
    <div className="stack-l">
      <header className="profile-head">
        <span className="profile-avatar" aria-hidden><UserRound size={30} /></span>
        <div className="grow stack-s" style={{ gap: 2 }}>
          <h1>{user.name}</h1>
          <p className="muted">
            Joined {new Date(user.joined).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })}
            {user.experience ? ` · ${EXPERIENCE[user.experience] ?? user.experience}` : ""}{user.goal ? ` · ${GOAL[user.goal] ?? user.goal}` : ""}
          </p>
        </div>
        <Link to="/settings" className="btn btn-small">Edit settings</Link>
      </header>
      <ProfileView profile={query.data} own />
    </div>
  );
}
