import {
  Activity,
  Code2,
  FolderKanban,
  ShieldCheck,
} from "lucide-react";

const features = [
  {
    title: "Project Management",
    description: "Manage all your software projects from one place.",
    icon: FolderKanban,
  },
  {
    title: "Development Tracking",
    description: "Track development progress, tasks and milestones.",
    icon: Code2,
  },
  {
    title: "System Monitoring",
    description: "Keep track of application status and maintenance.",
    icon: Activity,
  },
  {
    title: "Centralized Administration",
    description: "Manage your software portfolio securely.",
    icon: ShieldCheck,
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section className="mx-auto flex min-h-screen max-w-6xl flex-col justify-center px-6 py-20">

        <div className="mb-10 flex items-center gap-3">
          <div className="rounded-xl bg-blue-600 p-3">
            <Code2 size={28} />
          </div>

          <span className="text-xl font-bold tracking-tight">
            SherlskyyCommand
          </span>
        </div>

        <div className="max-w-3xl">
          <p className="mb-4 text-sm font-semibold uppercase tracking-[0.25em] text-blue-400">
            Developer Command Center
          </p>

          <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
            Your entire software portfolio.
            <span className="text-blue-500">
              {" "}One command center.
            </span>
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-400">
            Manage applications, organize development tasks,
            track milestones and administer your software projects
            through one centralized platform.
          </p>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => {
            const Icon = feature.icon;

            return (
              <div
                key={feature.title}
                className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 transition hover:border-blue-500/60"
              >
                <Icon className="mb-5 text-blue-400" size={28} />

                <h2 className="mb-2 text-lg font-semibold">
                  {feature.title}
                </h2>

                <p className="text-sm leading-6 text-slate-400">
                  {feature.description}
                </p>
              </div>
            );
          })}
        </div>

        <p className="mt-16 text-sm text-slate-500">
          SherlskyyCommand · Version 0.1.0 · Development
        </p>

      </section>
    </main>
  );
}