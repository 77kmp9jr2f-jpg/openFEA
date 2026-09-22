import type { Message } from "./types";

export function archiveConversation(messages: Message[]): Message[] {
  // Keep the full local record, including questions and review cards. Clone
  // it so later UI changes cannot alter a submitted analysis snapshot.
  return structuredClone(messages).map((message) => ({ ...message, live: !!message.live }));
}

export function assistantHistory(messages: Message[]) {
  // Bound remote context independently of local retention. Questions and
  // proposals are separate UI fields and must not disappear from the reply
  // context when the user answers or refers to one of them.
  return archiveConversation(messages.slice(-10)).map((message) => ({
    role: message.role,
    content: JSON.stringify(message),
  }));
}
