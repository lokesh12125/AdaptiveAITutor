import { type ReactNode, useEffect } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { Shell } from "./components/Shell";
import { EmptyState, PageLoading } from "./components/ui";
import { useSession } from "./lib/session";
import { AddQuestion, EditQuestion } from "./pages/AddQuestion";
import { AssessmentPage } from "./pages/Assessment";
import { Home } from "./pages/Home";
import { Library } from "./pages/Library";
import { Onboarding } from "./pages/Onboarding";
import { PathPage, UnitPage } from "./pages/Path";
import { ProgressPage } from "./pages/Progress";
import { SettingsPage } from "./pages/Settings";
import { TeacherPage, TeacherStudentPage } from "./pages/Teacher";
import { Welcome } from "./pages/Welcome";
import { WorkspacePage } from "./workspace/Workspace";

const TITLES: [RegExp, string][] = [
  [/^\/welcome/, "Welcome"], [/^\/onboarding/, "Getting started"], [/^\/path/, "Learning path"], [/^\/problems\/new/, "Add a question"], [/^\/problems$/, "Problems"], [/^\/progress/, "Your progress"], [/^\/teacher/, "Class"], [/^\/settings/, "Settings"], [/^\/check/, "Knowledge check"], [/^\/$/, "Home"],
];

function DocumentTitle() {
  const { pathname } = useLocation();
  useEffect(() => {
    const match = TITLES.find(([pattern]) => pattern.test(pathname));
    document.title = match ? `${match[1]} · Trellis` : "Trellis";
    if (!pathname.match(/^\/problems\/(?!new)/)) window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

function Authed({ children, role }: { children: ReactNode; role?: "student" | "teacher" }) {
  const { user, loading } = useSession();
  const location = useLocation();
  if (loading) return <div className="page"><PageLoading /></div>;
  if (!user) return <Navigate to="/welcome" replace state={{ from: location.pathname }} />;
  if (user.role === "student" && !user.onboarding_completed && location.pathname !== "/onboarding") return <Navigate to="/onboarding" replace />;
  if (role === "teacher" && user.role !== "teacher") return <Shell><EmptyState title="This page is only for teachers" action={<Link className="btn" to="/">Go home</Link>}>Your account does not have access to class data.</EmptyState></Shell>;
  if (role === "student" && user.role === "teacher") return <Navigate to="/teacher" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <>
      <DocumentTitle />
      <Routes>
        <Route path="/welcome" element={<Welcome />} />
        <Route path="/onboarding" element={<Authed><Onboarding /></Authed>} />
        <Route path="/" element={<Authed role="student"><Shell><Home /></Shell></Authed>} />
        <Route path="/path" element={<Authed role="student"><Shell><PathPage /></Shell></Authed>} />
        <Route path="/path/:unitId" element={<Authed role="student"><Shell><UnitPage /></Shell></Authed>} />
        <Route path="/problems" element={<Authed role="student"><Shell><Library /></Shell></Authed>} />
        <Route path="/problems/new" element={<Authed role="student"><Shell narrow><AddQuestion /></Shell></Authed>} />
        <Route path="/problems/:problemId/edit" element={<Authed role="student"><Shell narrow><EditQuestion /></Shell></Authed>} />
        <Route path="/problems/:problemId" element={<Authed role="student"><WorkspacePage /></Authed>} />
        <Route path="/progress" element={<Authed role="student"><Shell><ProgressPage /></Shell></Authed>} />
        <Route path="/check/:phase" element={<Authed role="student"><Shell narrow><AssessmentPage /></Shell></Authed>} />
        <Route path="/teacher" element={<Authed role="teacher"><Shell><TeacherPage /></Shell></Authed>} />
        <Route path="/teacher/:classId/students/:studentId" element={<Authed role="teacher"><Shell><TeacherStudentPage /></Shell></Authed>} />
        <Route path="/settings" element={<Authed><Shell narrow><SettingsPage /></Shell></Authed>} />
        <Route path="*" element={<div className="page"><EmptyState title="That page does not exist" action={<Link className="btn" to="/">Go home</Link>} /></div>} />
      </Routes>
    </>
  );
}
