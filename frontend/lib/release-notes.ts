import { readFile } from "node:fs/promises";
import path from "node:path";

export interface ReleaseNoteSection {
  title: string;
  changes: string[];
}

export interface ReleaseNotes {
  version: string;
  date: string | null;
  sections: ReleaseNoteSection[];
}

const releaseHeadingPattern =
  /^## \[([^\]]+)\](?:\([^)]+\))?(?:\s+-\s+(\d{4}-\d{2}-\d{2})|\s+\((\d{4}-\d{2}-\d{2})\))?\s*$/;

function cleanMarkdownText(text: string): string {
  return text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[`*_]/g, "")
    .trim();
}

function parseReleaseNotes(changelog: string): ReleaseNotes | null {
  const lines = changelog.split(/\r?\n/);
  const releaseIndexes: Array<{
    index: number;
    version: string;
    date: string | null;
  }> = [];

  for (const [index, line] of lines.entries()) {
    const match = releaseHeadingPattern.exec(line);
    if (match && match[1].toLowerCase() !== "unreleased") {
      releaseIndexes.push({
        index,
        version: match[1],
        date: match[2] ?? match[3] ?? null,
      });
    }
  }

  const latest = releaseIndexes[0];
  if (!latest) {
    return null;
  }

  const nextReleaseIndex = releaseIndexes[1]?.index ?? lines.length;
  const sections: ReleaseNoteSection[] = [];
  let currentSection: ReleaseNoteSection | undefined;

  for (const line of lines.slice(latest.index + 1, nextReleaseIndex)) {
    const headingMatch = /^###\s+(.+?)\s*$/.exec(line);
    if (headingMatch) {
      currentSection = {
        title: cleanMarkdownText(headingMatch[1]),
        changes: [],
      };
      sections.push(currentSection);
      continue;
    }

    const changeMatch = /^\s*[-*]\s+(.+?)\s*$/.exec(line);
    if (!changeMatch) {
      continue;
    }

    if (!currentSection) {
      currentSection = { title: "Changes", changes: [] };
      sections.push(currentSection);
    }
    currentSection.changes.push(cleanMarkdownText(changeMatch[1]));
  }

  return {
    version: latest.version,
    date: latest.date,
    sections: sections.filter((section) => section.changes.length > 0),
  };
}

export async function getLatestReleaseNotes(): Promise<ReleaseNotes | null> {
  const changelogPath = path.resolve(process.cwd(), "..", "CHANGELOG.md");
  const changelog = await readFile(changelogPath, "utf8");

  return parseReleaseNotes(changelog);
}
