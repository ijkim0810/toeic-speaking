function activeWordIndex(words, t) {
  for (let i = 0; i < words.length; i++) {
    if (t >= words[i].start && t < words[i].end) return i;
  }
  return -1;
}

function buildSchedule(sentence, repeats) {
  const out = [{ lang: "ko", text: sentence.ko, audio: sentence.koAudio }];
  for (let i = 0; i < repeats; i++) {
    out.push({ lang: "en", text: sentence.en, audio: sentence.enAudio });
  }
  return out;
}

if (typeof module !== "undefined") {
  module.exports = { activeWordIndex, buildSchedule };
}
