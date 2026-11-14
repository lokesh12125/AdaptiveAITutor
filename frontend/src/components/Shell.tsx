import * as Menu from "@radix-ui/react-dropdown-menu";
import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, ChartLine, GraduationCap, House, ListChecks, LogOut, Moon, Plus, Search, Settings as SettingsIcon, Sun, UserRound } from "lucide-react";
import { type FormEvent, type ReactNode, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { useSession } from "@/lib/session";

import { Button, Tip } from "./ui";

export function LogoMark({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden>
      <circle cx="5.5" cy="18.5" r="2.5" fill="currentColor" />
      <circle cx="18.5" cy="5.5" r="2.5" />
      <path d="M8 18.5h5.5a3.5 3.5 0 0 0 0-7h-3a3.5 3.5 0 0 1 0-7H16" />
    </svg>
  );
}

export function Logo() {
  return <Link to="/" className="logo"><LogoMark /> CodePath</Link>;
}

/** A small dotted route with a yellow goal. Decoration only. */
export function RouteArt({ className = "spotlight-art" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 400 200" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" strokeDasharray="1 14" aria-hidden>
      <path d="M12 184C84 184 74 110 154 110S234 150 274 90 330 28 380 24" />
      <g fill="currentColor" stroke="none"><circle cx="12" cy="184" r="10" /><circle cx="154" cy="110" r="10" /><circle cx="274" cy="90" r="10" /></g>
      <circle className="goal" cx="380" cy="24" r="16" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function ThemeToggle({ className }: { className?: string }) {
  const { updatePreferences } = useSession();
  const dark = document.documentElement.dataset.theme === "dark";
  return (
    <Tip text={dark ? "Switch to light theme" : "Switch to dark theme"}>
      <Button variant="ghost" icon className={className} aria-label={dark ? "Switch to light theme" : "Switch to dark theme"} onClick={() => void updatePreferences({ theme: dark ? "light" : "dark" })}>
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

/** Search from anywhere. On small screens it is a link to the search page, to keep the bar clear. */
function NavSearch() {
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (text.trim()) navigate(`/search?q=${encodeURIComponent(text.trim())}`);
    setText("");
  };
  return (
    <>
      <form className="nav-search hide-narrow" role="search" onSubmit={submit}>
        <Search size={14} aria-hidden />
        <input className="input" aria-label="Search topics and problems" placeholder="Search" value={text} onChange={(event) => setText(event.target.value)} data-testid="nav-search" />
      </form>
      <Link to="/search" className="btn btn-ghost btn-icon show-narrow" aria-label="Search topics and problems"><Search size={17} aria-hidden /></Link>
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
        { to: "/path", label: "Learn", icon: BookOpen },
        { to: "/problems", label: "Practice", icon: ListChecks },
        { to: "/progress", label: "Progress", icon: ChartLine },
        { to: "/profile", label: "Profile", icon: UserRound },
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
      <header className="topnav">
        <div className="topnav-inner">
          <Logo />
          <nav className="nav-links" aria-label="Main">
            {links.map((link) => <NavLink key={link.to} to={link.to} end={link.to === "/"}>{link.label}</NavLink>)}
          </nav>
          <div className="grow" />
          {!teacher && <NavSearch />}
          {!teacher && <Link to="/problems/new" className="btn btn-small hide-mobile"><Plus size={15} aria-hidden /> Add question</Link>}
          <ThemeToggle />
          <Menu.Root>
            <Menu.Trigger asChild><Button variant="ghost" icon aria-label="Account menu"><UserRound size={17} aria-hidden /></Button></Menu.Trigger>
            <Menu.Portal>
              <Menu.Content className="menu" align="end" sideOffset={6}>
                <div className="menu-label">{user?.name}{user?.is_demo ? " (demo)" : ""}</div>
                {!teacher && <Menu.Item asChild className="menu-item"><Link to="/profile" data-testid="menu-profile"><UserRound size={15} aria-hidden /> Your profile</Link></Menu.Item>}
                {!teacher && <Menu.Item asChild className="menu-item show-mobile"><Link to="/problems/new"><Plus size={15} aria-hidden /> Add question</Link></Menu.Item>}
                <Menu.Item asChild className="menu-item"><Link to="/settings"><SettingsIcon size={15} aria-hidden /> Settings</Link></Menu.Item>
                <Menu.Separator className="menu-separator" />
                <Menu.Item className="menu-item" onSelect={() => void signOut()}><LogOut size={15} aria-hidden /> Sign out</Menu.Item>
              </Menu.Content>
            </Menu.Portal>
          </Menu.Root>
        </div>
      </header>
      <main id="main" className={`page ${narrow ? "page-narrow" : ""}`} tabIndex={-1}>{children}</main>
      <nav className="bottom-nav" aria-label="Main, mobile">
        {links.map((link) => <NavLink key={link.to} to={link.to} end={link.to === "/"}><link.icon size={19} aria-hidden />{link.label}</NavLink>)}
        {teacher && <NavLink to="/settings"><SettingsIcon size={19} aria-hidden />Settings</NavLink>}
      </nav>
    </div>
  );
}
