const test = require("node:test");
const assert = require("node:assert");
const { activeWordIndex } = require("./player-core.js");

test("activeWordIndex finds current word", () => {
  const words = [{ text: "He", start: 0.0, end: 0.2 }, { text: "is", start: 0.3, end: 0.5 }];
  assert.strictEqual(activeWordIndex(words, 0.1), 0);
  assert.strictEqual(activeWordIndex(words, 0.4), 1);
  assert.strictEqual(activeWordIndex(words, 0.25), -1);
  assert.strictEqual(activeWordIndex(words, 9), -1);
});
