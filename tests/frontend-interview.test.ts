import { test } from "node:test";
import assert from "node:assert/strict";
import { archiveConversation, assistantHistory } from "../frontend/src/interview.ts";
import { demoGeometry } from "../frontend/src/types.ts";
import type { Message } from "../frontend/src/types.ts";

function interview(): Message[] {
  return Array.from({ length: 36 }, (_, i) => ({
    role: i % 2 ? "assistant" : "user",
    text: i === 0 ? "Original requirement: preserve this load case." : `Message ${i}`,
    ...(i % 2 ? { questions: [`Question ${i}?`], live: true } : {}),
  }));
}

test("analysis archives the complete interview and structured review cards", () => {
  const messages = interview();
  messages[3].proposal = { ...demoGeometry, name: "Earlier geometry" };
  messages[3].interviewFor = "a".repeat(32);
  const saved = archiveConversation(messages);
  assert.equal(saved.length, 36);
  assert.equal(saved[0].text, messages[0].text);
  assert.deepEqual(saved[3], messages[3]);
  assert.equal(saved[0].live, false);
  messages[3].questions![0] = "Changed later";
  assert.equal(saved[3].questions![0], "Question 3?");
});

test("Astra receives a bounded recent context including its questions and proposal", () => {
  const messages = interview();
  messages[35].proposal = { ...demoGeometry, name: "Review this proposal" };
  const history = assistantHistory(messages);
  assert.equal(history.length, 10);
  assert.equal(history[0].role, messages[26].role);
  const last = JSON.parse(history[9].content);
  assert.equal(last.text, "Message 35");
  assert.deepEqual(last.questions, ["Question 35?"]);
  assert.equal(last.proposal.name, "Review this proposal");
  assert.equal(last.live, true);
});
