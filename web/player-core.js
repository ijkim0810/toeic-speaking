function activeWordIndex(words, t) {
  for (let i = 0; i < words.length; i++) {
    if (t >= words[i].start && t < words[i].end) return i;
  }
  return -1;
}

if (typeof module !== "undefined") {
  module.exports = { activeWordIndex };
}
