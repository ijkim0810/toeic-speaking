const test = require("node:test");
const assert = require("node:assert");
const { activeWordIndex, buildSchedule } = require("./player-core.js");

test("activeWordIndex finds current word", () => {
  const words = [{ text: "He", start: 0.0, end: 0.2 }, { text: "is", start: 0.3, end: 0.5 }];
  assert.strictEqual(activeWordIndex(words, 0.1), 0);
  assert.strictEqual(activeWordIndex(words, 0.4), 1);
  assert.strictEqual(activeWordIndex(words, 0.25), -1);
  assert.strictEqual(activeWordIndex(words, 9), -1);
});

test("buildSchedule = 1 korean then N english", () => {
  const s = { en: "Hi.", ko: "안녕.", enAudio: "audio/e.mp3", koAudio: "audio/k.mp3" };
  const sched = buildSchedule(s, 5);
  assert.strictEqual(sched.length, 6);
  assert.deepStrictEqual(sched[0], { lang: "ko", text: "안녕.", audio: "audio/k.mp3" });
  assert.strictEqual(sched[1].lang, "en");
  assert.strictEqual(sched[5].lang, "en");
});
