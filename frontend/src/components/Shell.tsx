import * as Menu from "@radix-ui/react-dropdown-menu";
import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, ChartLine, GraduationCap, House, ListChecks, LogOut, Moon, Plus, Settings as SettingsIcon, Sun, UserRound } from "lucide-react";
import { type ReactNode } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { useSession } from "@/lib/session";

import { Button, Tip } from "./ui";

export function LogoMark({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
      <path d="M6.5 21V3M12 21V3M17.5 21V3M3 8h18M3 16h18" />
    </svg>
  );
}

export function Logo() {
  return <Link to="/" className="logo"><LogoMark /> Trellis</Link>;
}

export function ThemeToggle() {
  const { updatePreferences } = useSession();
  const dark = document.documentElement.dataset.theme === "dark";
  return (
    <Tip text={dark ? "Switch to light theme" : "Switch to dark theme"}>
      <Button variant="ghost" icon aria-label={dark ? "Switch to light theme" : "Switch to dark theme"} onClick={() => void updatePreferences({ theme: dark ? "light" : "dark" })}>
        {dark ? <Sun size={17} aria-hidden /> : <Moon size={17} aria-hidden />}
      </Button>
    </Tip>
  );
}

export function SystemBanners() {
  const { user, status } = useSession();
  return (
    <>
      {user?.is_demo && (
        <div className="banner banner-demo" role="status">
          <span><strong>Demo session.</strong> This is not a secure account, and its data may be reset. {user.role === "teacher" ? "The class shown is synthetic." : "Please don't enter personal information."}</span>
        </div>
      )}
      {status && !status.execution.available && (
        <div className="banner banner-danger" role="alert"><span><strong>Code checking is unavailable right now.</strong> You can keep writing. Your work is saved, and running will work again when the service returns.</span></div>
      )}
      {status && status.execution.available && !status.execution.secure && (
        <div className="banner banner-warn" role="status"><span><strong>Development mode:</strong> code runs without container isolation on this server. Use it only with code you trust.</span></div>
      )}
    </>
  );
}

export function Shell({ children, narrow }: { children: ReactNode; narrow?: boolean }) {
  const { user, setUser } = useSession();
  const navigate = useNavigate();
  const client = useQueryClient();
  const teacher = user?.role === "teacher";
  const links = teacher
    ? [{ to: "/teacher", label: "Class", icon: GraduationCap }]
    : [
        { to: "/", label: "Home", icon: House },
        { to: "/path", label: "Path", icon: BookOpen },
        { to: "/problems", label: "Problems", icon: ListChecks },
        { to: "/progress", label: "Progress", icon: ChartLine },
      ];
  const signOut = async () => {
    await api("/auth/logout", { method: "POST" });
    setUser(null);
    client.clear();
    navigate("/welcome");
  };
  return (
    <div className="app">
      <a className="skip-link" href="#main">Skip to main content</a>
      <SystemBanners />
      <header className="topbar">
        <Logo />
        <nav className="nav" aria-label="Main">
          {links.map((link) => <NavLink key={link.to} to={link.to} end={link.to === "/"}>{link.label}</NavLink>)}
        </nav>
        <div className="grow" />
        {!teacher && <Link to="/problems/new" className="btn btn-small hide-mobile"><Plus size={15} aria-hidden /> Add question</Link>}
        <ThemeToggle />
        <Menu.Root>
          <Menu.Trigger asChild><Button variant="ghost" icon aria-label="Account menu"><UserRound size={17} aria-hidden /></Button></Menu.Trigger>
          <Menu.Portal>
            <Menu.Content className="menu" align="end" sideOffset={6}>
              <div className="menu-label">{user?.name}{user?.is_demo ? " (demo)" : ""}</div>
              {!teacher && <Menu.Item asChild className="menu-item show-mobile"><Link to="/problems/new"><Plus size={15} aria-hidden /> Add question</Link></Menu.Item>}
              <Menu.Item asChild className="menu-item"><Link to="/settings"><SettingsIcon size={15} aria-hidden /> Settings</Link></Menu.Item>
              <Menu.Separator className="menu-separator" />
              <Menu.Item className="menu-item" onSelect={() => void signOut()}><LogOut size={15} aria-hidden /> Sign out</Menu.Item>
            </Menu.Content>
          </Menu.Portal>
        </Menu.Root>
      </header>
      <main id="main" className={`page ${narrow ? "page-narrow" : ""}`} tabIndex={-1}>{children}</main>
      <nav className="bottom-nav" aria-label="Main, mobile">
        {links.map((link) => <NavLink key={link.to} to={link.to} end={link.to === "/"}><link.icon size={19} aria-hidden />{link.label}</NavLink>)}
        <NavLink to="/settings"><SettingsIcon size={19} aria-hidden />Settings</NavLink>
      </nav>
    </div>
  );
}
