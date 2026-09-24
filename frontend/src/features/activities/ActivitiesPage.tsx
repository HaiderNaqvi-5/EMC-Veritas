import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "../../components/ui/Skeleton";
import { apiRequest } from "../../lib/api/client";
import { approveTemplate, configureTemplate, TemplateField, uploadTemplate } from "../../api/templates/admin";

type Activity = {
  id: string;
  session_id: string;
  name: string;
  description: string | null;
  activity_date: string;
  template_id: string | null;
  status: string;
};
type Student = {
  id: string;
  roll_number: string;
  full_name: string;
  active: boolean;
};
type Participant = { id: string; student_id: string; eligible: boolean };
type ApprovedTemplate = { id: string; name: string };
type EmcSession = {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: string;
};

export function ActivitiesPage() {
  const client = useQueryClient();
  const [sessionId, setSessionId] = useState("");
  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [certificateFile, setCertificateFile] = useState<File | null>(null);
  const [activityId, setActivityId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [participantFile, setParticipantFile] = useState<File | null>(null);
  const [viewId, setViewId] = useState("");
  const activities = useQuery({
    queryKey: ["admin", "activities"],
    queryFn: () => apiRequest<Activity[]>("/admin/activities"),
  });
  const sessions = useQuery({
    queryKey: ["admin", "sessions"],
    queryFn: () => apiRequest<EmcSession[]>("/admin/sessions"),
  });
  const students = useQuery({
    queryKey: ["admin", "students"],
    queryFn: () => apiRequest<Student[]>("/admin/students"),
  });
  const templates = useQuery({
    queryKey: ["admin", "approved-templates"],
    queryFn: () =>
      apiRequest<ApprovedTemplate[]>("/admin/activities/templates"),
  });
  const participants = useQuery({
    queryKey: ["admin", "activity", viewId, "participants"],
    queryFn: () =>
      apiRequest<Participant[]>(`/admin/activities/${viewId}/participants`),
    enabled: !!viewId,
  });
  const refreshActivities = () =>
    client.invalidateQueries({ queryKey: ["admin", "activities"] });
  const refreshParticipants = () =>
    client.invalidateQueries({
      queryKey: ["admin", "activity", viewId, "participants"],
    });
  const create = useMutation({
    mutationFn: async () => {
      const activity = await apiRequest<Activity>("/admin/activities", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, name, activity_date: date }),
      });
      if (certificateFile) {
        const template = await uploadTemplate(`${name} certificate`, certificateFile);
        const fields: TemplateField[] = ["student_name", "roll_number", "activity_name", "activity_date"].map((field_name, index) => ({ field_name, page_number: 1, x: 100, y: 160 + index * 55, width: 300, height: 30 }));
        await configureTemplate(template.id, fields, "retain");
        await approveTemplate(template.id);
        await apiRequest<Activity>(`/admin/activities/${activity.id}`, { method: "PUT", body: JSON.stringify({ name: activity.name, description: activity.description, activity_date: activity.activity_date, template_id: template.id }) });
      }
      return activity;
    },
    onSuccess: () => {
      setName("");
      setDate("");
      setCertificateFile(null);
      void refreshActivities();
    },
  });
  const update = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Pick<
        Activity,
        "name" | "description" | "activity_date" | "template_id"
      >;
    }) =>
      apiRequest<Activity>(`/admin/activities/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => void refreshActivities(),
  });
  const status = useMutation({
    mutationFn: ({ id, value }: { id: string; value: string }) =>
      apiRequest<Activity>(`/admin/activities/${id}/status`, {
        method: "POST",
        body: JSON.stringify({ status: value }),
      }),
    onSuccess: () => void refreshActivities(),
  });
  const add = useMutation({
    mutationFn: () =>
      apiRequest(`/admin/activities/${activityId}/participants`, {
        method: "POST",
        body: JSON.stringify({ student_id: studentId, eligible: true }),
      }),
    onSuccess: () => {
      setViewId(activityId);
      setStudentId("");
      void refreshParticipants();
    },
  });
  const eligibility = useMutation({
    mutationFn: ({ id, value }: { id: string; value: boolean }) =>
      apiRequest(`/admin/activities/${viewId}/participants/${id}/eligibility`, {
        method: "POST",
        body: JSON.stringify({ eligible: value }),
      }),
    onSuccess: () => void refreshParticipants(),
  });
  const issue = useMutation({
    mutationFn: (id: string) =>
      apiRequest(`/admin/documents/activities/${id}/issue`, { method: "POST" }),
    onSuccess: () => void refreshActivities(),
  });
  const participantImport = useMutation({ mutationFn: async () => { const data = new FormData(); data.set("file", participantFile as File); return apiRequest<{ added: number; already_present: number; unknown_roll_numbers: string[] }>(`/admin/imports/activities/${activityId}/participants/import`, { method: "POST", body: data }); }, onSuccess: () => { setParticipantFile(null); setViewId(activityId); void refreshParticipants(); } });
  const error =
    create.error?.message ??
    update.error?.message ??
    status.error?.message ??
    add.error?.message ??
    eligibility.error?.message ??
    issue.error?.message ??
    participantImport.error?.message ??
    participants.error?.message ??
    sessions.error?.message;
  // Keep participant name lookup O(n) even for large activity lists.
  const studentMap = useMemo(
    () =>
      new Map((students.data ?? []).map((student) => [student.id, student])),
    [students.data],
  );
  function addActivity(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }
  function addParticipant(event: FormEvent) {
    event.preventDefault();
    add.mutate();
  }
  function edit(event: FormEvent<HTMLFormElement>, item: Activity) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    update.mutate({
      id: item.id,
      payload: {
        name: String(form.get("name")),
        description: String(form.get("description")) || null,
        activity_date: String(form.get("activity_date")),
        template_id: String(form.get("template_id")) || null,
      },
    });
  }
  const activeSessions =
    sessions.data?.filter((item) => item.status === "ACTIVE") ?? [];
  return (
    <section>
      <h1 className="text-3xl font-bold">Activities</h1>
      <p className="mt-2 text-slate-600 dark:text-slate-400">
        Create, edit, archive, and issue activities while keeping participant
        eligibility server-authoritative.
      </p>
      <form
        onSubmit={addActivity}
        className="mt-6 grid gap-3 rounded-xl border p-4 md:grid-cols-5"
      >
        <select
          aria-label="Active session"
          required
          value={sessionId}
          onChange={(e) => setSessionId(e.target.value)}
          className="rounded border p-2"
        >
          <option value="">Choose active session</option>
          {activeSessions.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name} · {item.start_date} to {item.end_date}
            </option>
          ))}
        </select>
        <input
          aria-label="Activity date"
          required
          placeholder="Activity name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="rounded border p-2"
        />
        <input
          required
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded border p-2"
        />
        <input required accept="application/pdf" type="file" onChange={(event) => setCertificateFile(event.target.files?.[0] ?? null)} className="rounded border p-2" />
        <button
          disabled={create.isPending || !activeSessions.length}
          className="rounded bg-slate-900 p-2 text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          Create activity
        </button>
      </form>
      <p className="mt-2 text-sm text-slate-500">A certificate PDF is required here and is automatically attached, configured, and approved for this activity.</p>
      {sessions.isSuccess && !activeSessions.length && (
        <p className="mt-2 text-sm text-slate-500">
          Create or activate an EMC session before adding an activity.
        </p>
      )}
      <form
        onSubmit={addParticipant}
        className="mt-4 grid gap-3 rounded-xl border p-4 md:grid-cols-3"
      >
        <select
          aria-label="Activity for participant"
          required
          value={activityId}
          onChange={(e) => setActivityId(e.target.value)}
          className="rounded border p-2"
        >
          <option value="">Choose activity</option>
          {activities.data?.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Eligible student"
          required
          value={studentId}
          onChange={(e) => setStudentId(e.target.value)}
          className="rounded border p-2"
        >
          <option value="">Choose active student</option>
          {students.data
            ?.filter((item) => item.active)
            .map((item) => (
              <option key={item.id} value={item.id}>
                {item.roll_number} — {item.full_name}
              </option>
            ))}
        </select>
        <button className="rounded bg-slate-900 p-2 text-white">
          Add eligible participant
        </button>
      </form>
      <form onSubmit={(event) => { event.preventDefault(); if (participantFile) participantImport.mutate(); }} className="mt-4 grid gap-3 rounded-xl border p-4 md:grid-cols-3"><select required value={activityId} onChange={(e) => setActivityId(e.target.value)} className="rounded border p-2"><option value="">Choose activity for participant Excel</option>{activities.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><input required accept=".xlsx" type="file" onChange={(event) => setParticipantFile(event.target.files?.[0] ?? null)} className="rounded border p-2"/><button disabled={!participantFile || participantImport.isPending} className="rounded bg-slate-900 p-2 text-white">Import participant Excel</button></form>
      {participantImport.data && <p role="status" className="mt-2 text-sm text-green-700">Imported {participantImport.data.added} participants; {participantImport.data.already_present} were already linked.{participantImport.data.unknown_roll_numbers.length ? ` Unknown active roll numbers: ${participantImport.data.unknown_roll_numbers.join(", ")}` : ""}</p>}
      {error && (
        <p role="alert" className="mt-3 rounded bg-red-50 p-3 text-red-700">
          {error}
        </p>
      )}
      <div className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        {activities.isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <ul className="space-y-3">
            {activities.data?.map((item) => (
              <li key={item.id} className="rounded border p-4">
                <strong>{item.name}</strong> — {item.activity_date} —{" "}
                {item.status}
                <div className="mt-3 flex flex-wrap gap-3">
                  <select
                    aria-label={`Status for ${item.name}`}
                    value={item.status}
                    onChange={(e) =>
                      status.mutate({ id: item.id, value: e.target.value })
                    }
                    className="rounded border p-1"
                  >
                    <option value={item.status}>{item.status}</option>
                    {item.status === "DRAFT" && (
                      <option value="READY">READY</option>
                    )}
                    {item.status === "PUBLISHED" && (
                      <option value="ARCHIVED">ARCHIVED</option>
                    )}
                  </select>
                  <button
                    onClick={() => setViewId(item.id)}
                    className="underline"
                  >
                    Participants
                  </button>
                  <button
                    onClick={() => issue.mutate(item.id)}
                    disabled={item.status !== "READY"}
                    className="underline"
                  >
                    Issue and publish certificates
                  </button>
                </div>
                <details className="mt-3">
                  <summary className="cursor-pointer text-sm underline">
                    Edit activity
                  </summary>
                  <form
                    onSubmit={(e) => edit(e, item)}
                    className="mt-3 grid gap-2 md:grid-cols-3"
                  >
                    <input
                      aria-label={`Name for ${item.name}`}
                      name="name"
                      defaultValue={item.name}
                      required
                      className="rounded border p-2"
                    />
                    <input
                      aria-label={`Date for ${item.name}`}
                      name="activity_date"
                      defaultValue={item.activity_date}
                      required
                      type="date"
                      className="rounded border p-2"
                    />
                    <select
                      aria-label={`Template for ${item.name}`}
                      name="template_id"
                      defaultValue={item.template_id ?? ""}
                      className="rounded border p-2"
                    >
                      <option value="">No template selected</option>
                      {templates.data?.map((template) => (
                        <option key={template.id} value={template.id}>
                          {template.name}
                        </option>
                      ))}
                    </select>
                    <button className="rounded border p-2">Save</button>
                    <textarea
                      name="description"
                      defaultValue={item.description ?? ""}
                      placeholder="Description"
                      className="rounded border p-2 md:col-span-3"
                    />
                  </form>
                </details>
              </li>
            ))}
          </ul>
        )}
        <aside className="rounded-xl border p-4">
          <h2 className="font-semibold">Participant eligibility</h2>
          {!viewId ? (
            <p className="mt-2 text-sm text-slate-500">Select an activity.</p>
          ) : participants.isLoading ? (
            <Skeleton className="mt-4 h-32 w-full" />
          ) : (
            <ul className="mt-4 space-y-2">
              {participants.data?.map((participant) => (
                <li
                  key={participant.id}
                  className="flex items-center justify-between gap-2 rounded border p-2"
                >
                  <span>
                    {studentMap.get(participant.student_id)?.full_name ??
                      participant.student_id}
                  </span>
                  <button
                    onClick={() =>
                      eligibility.mutate({
                        id: participant.id,
                        value: !participant.eligible,
                      })
                    }
                    className="rounded border px-2 py-1 text-sm"
                  >
                    {participant.eligible ? "Eligible" : "Ineligible"}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </section>
  );
}
