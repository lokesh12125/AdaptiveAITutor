import React from 'react';
import ProblemSidebar from './ProblemSidebar';
import CodeWorkspace from './CodeWorkspace';
import AgentFeedbackSidebar from './AgentFeedbackSidebar';

export default function PracticeLab({
  problemSearch,
  setProblemSearch,
  filteredProblems,
  expandedTopics,
  toggleTopic,
  problem,
  selectProblem,
  code,
  setCode,
  activeSeconds,
  setActiveSeconds,
  setIsTimerRunning,
  runLoading,
  submitLoading,
  handleRunCode,
  handleSubmitCode,
  runResult,
  setRunResult,
  submitResult,
  setSubmitResult,
  problems
}) {
  return (
    <div className="practice-layout">
      {/* Left: Problem Navigator */}
      <ProblemSidebar
        problemSearch={problemSearch}
        setProblemSearch={setProblemSearch}
        filteredProblems={filteredProblems}
        expandedTopics={expandedTopics}
        toggleTopic={toggleTopic}
        problem={problem}
        selectProblem={selectProblem}
      />

      {/* Center: Coding Workspace & Results */}
      <CodeWorkspace
        problem={problem}
        code={code}
        setCode={setCode}
        activeSeconds={activeSeconds}
        setActiveSeconds={setActiveSeconds}
        setIsTimerRunning={setIsTimerRunning}
        runLoading={runLoading}
        submitLoading={submitLoading}
        handleRunCode={handleRunCode}
        handleSubmitCode={handleSubmitCode}
        runResult={runResult}
        setRunResult={setRunResult}
        submitResult={submitResult}
        setSubmitResult={setSubmitResult}
      />

      {/* Right Sidebar: Agent Pipeline Activity & Live Cognitive Signals */}
      <AgentFeedbackSidebar
        submitResult={submitResult}
        problems={problems}
        selectProblem={selectProblem}
      />
    </div>
  );
}
