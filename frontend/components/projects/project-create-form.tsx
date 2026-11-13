
"use client";

import { useState } from "react";
import axios from "axios";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { AlertCircle, Loader2, Plus, X } from "lucide-react";

import {
  createProject,
  type Project,
} from "../../lib/project-service";

// ---------------------------------------------------------
// Validation
// ---------------------------------------------------------

const projectCreateSchema = z.object({
  name: z
    .string()
    .trim()
    .min(2, "Project name must contain at least 2 characters.")
    .max(150, "Project name cannot exceed 150 characters."),

  description: z
    .string()
    .max(2000, "Description cannot exceed 2,000 characters."),
});

type ProjectFormValues = z.infer<typeof projectCreateSchema>;

// ---------------------------------------------------------
// Component properties
// ---------------------------------------------------------

interface ProjectCreateFormProps {
  accessToken: string;
  onCreated: (project: Project) => void;
  onCancel: () => void;
}

// ---------------------------------------------------------
// Project creation form
// ---------------------------------------------------------

export default function ProjectCreateForm({
  accessToken,
  onCreated,
  onCancel,
}: ProjectCreateFormProps) {
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ProjectFormValues>({
    resolver: zodResolver(projectCreateSchema),
    defaultValues: {
      name: "",
      description: "",
    },
  });

  async function handleProjectCreation(values: ProjectFormValues) {
    setServerError(null);

    try {
      const project = await createProject(accessToken, {
        name: values.name,
        description: values.description.trim() || null,
      });

      onCreated(project);
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;

        if (typeof detail === "string") {
          setServerError(detail);
        } else if (Array.isArray(detail)) {
          setServerError(
            "Some project details are invalid. Please review your input.",
          );
        } else {
          setServerError(
            "We couldn't create your project. Please try again.",
          );
        }

        return;
      }

      setServerError(
        "An unexpected error occurred while creating your project.",
      );
    }
  }

  return (
    <section
      aria-labelledby="create-project-heading"
      className="rounded-2xl border border-blue-500/30 bg-slate-900/80 p-5 sm:p-6"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-blue-500/10 p-2 text-blue-400">
              <Plus size={19} />
            </div>

            <h4
              id="create-project-heading"
              className="text-lg font-semibold"
            >
              Create a project
            </h4>
          </div>

          <p className="mt-2 text-sm text-slate-400">
            Add a software project to your command center.
          </p>
        </div>

        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          aria-label="Close project creation form"
          className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white disabled:opacity-50"
        >
          <X size={19} />
        </button>
      </div>

      <form
        onSubmit={handleSubmit(handleProjectCreation)}
        className="mt-6 space-y-5"
        noValidate
      >
        {/* Project name */}
        <div>
          <label
            htmlFor="project-name"
            className="mb-2 block text-sm font-medium text-slate-200"
          >
            Project name <span className="text-red-400">*</span>
          </label>

          <input
            id="project-name"
            type="text"
            maxLength={150}
            autoComplete="off"
            placeholder="e.g. AgriCore"
            aria-invalid={Boolean(errors.name)}
            aria-describedby={
              errors.name ? "project-name-error" : undefined
            }
            {...register("name")}
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
          />

          {errors.name && (
            <p
              id="project-name-error"
              role="alert"
              className="mt-2 text-xs text-red-400"
            >
              {errors.name.message}
            </p>
          )}
        </div>

        {/* Description */}
        <div>
          <label
            htmlFor="project-description"
            className="mb-2 block text-sm font-medium text-slate-200"
          >
            Description
          </label>

          <textarea
            id="project-description"
            rows={4}
            maxLength={2000}
            placeholder="Describe what this project does and what you are building..."
            aria-invalid={Boolean(errors.description)}
            aria-describedby={
              errors.description
                ? "project-description-error"
                : undefined
            }
            {...register("description")}
            className="w-full resize-y rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
          />

          {errors.description && (
            <p
              id="project-description-error"
              role="alert"
              className="mt-2 text-xs text-red-400"
            >
              {errors.description.message}
            </p>
          )}

          <p className="mt-2 text-xs text-slate-500">
            Maximum 2,000 characters. You can leave this empty.
          </p>
        </div>

        {/* API error */}
        {serverError && (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300"
          >
            <AlertCircle size={18} className="mt-0.5 shrink-0" />
            <p>{serverError}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="rounded-xl border border-slate-700 px-5 py-3 text-sm font-medium text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancel
          </button>

          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={17} className="animate-spin" />
                Creating project...
              </>
            ) : (
              <>
                <Plus size={17} />
                Create project
              </>
            )}
          </button>
        </div>
      </form>
    </section>
  );
}
