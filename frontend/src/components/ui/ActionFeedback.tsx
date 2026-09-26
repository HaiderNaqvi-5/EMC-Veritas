import { useEffect, useState } from "react";
import { useIsMutating } from "@tanstack/react-query";
import {
  ACTION_FEEDBACK_EVENT,
  type ActionFeedbackDetail,
} from "../../lib/feedback/actions";

type Notice = ActionFeedbackDetail & { id: number };

export function ActionFeedback() {
  const pendingActions = useIsMutating();
  const [notices, setNotices] = useState<Notice[]>([]);

  useEffect(() => {
    const showNotice = (event: Event) => {
      const detail = (event as CustomEvent<ActionFeedbackDetail>).detail;
      if (!detail?.message) return;
      const notice = { ...detail, id: Date.now() + Math.floor(Math.random() * 1_000) };
      setNotices((current) => [...current.slice(-2), notice]);
      window.setTimeout(() => {
        setNotices((current) => current.filter((item) => item.id !== notice.id));
      }, detail.kind === "error" ? 8_000 : 4_500);
    };
    window.addEventListener(ACTION_FEEDBACK_EVENT, showNotice);
    return () => window.removeEventListener(ACTION_FEEDBACK_EVENT, showNotice);
  }, []);

  return (
    <div className="action-feedback" aria-live="polite" aria-relevant="additions">
      {pendingActions > 0 && (
        <div className="action-feedback__toast action-feedback__toast--working" role="status">
          <span className="action-feedback__spinner" aria-hidden="true" />
          Processing your request…
        </div>
      )}
      {notices.map((notice) => (
        <div
          key={notice.id}
          className={`action-feedback__toast action-feedback__toast--${notice.kind}`}
          role={notice.kind === "error" ? "alert" : "status"}
        >
          <strong>{notice.kind === "success" ? "Completed" : "Action failed"}</strong>
          <span>{notice.message}</span>
        </div>
      ))}
    </div>
  );
}
