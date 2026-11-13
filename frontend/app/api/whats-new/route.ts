import { getLatestReleaseNotes } from "../../../lib/release-notes";

export async function GET() {
  const release = await getLatestReleaseNotes();

  if (!release) {
    return Response.json(
      { error: "No published release notes are available." },
      {
        status: 404,
        headers: { "Cache-Control": "no-store" },
      },
    );
  }

  return Response.json(release, {
    headers: { "Cache-Control": "no-store" },
  });
}
