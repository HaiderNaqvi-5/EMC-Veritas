export type ActionFeedbackKind = "success" | "error";

export type ActionFeedbackDetail = {
  kind: ActionFeedbackKind;
  message: string;
};

export const ACTION_FEEDBACK_EVENT = "emc:action-feedback";

export function notifyAction(kind: ActionFeedbackKind, message: string): void {
  window.dispatchEvent(
    new CustomEvent<ActionFeedbackDetail>(ACTION_FEEDBACK_EVENT, { detail: { kind, message } }),
  );
}
